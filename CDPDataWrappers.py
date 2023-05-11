import  sys, os, time, signal, random, json, cdp, re, copy
from    util import *
from    colorama import Fore, Back, Style, init as colorama_init
import  ChromeClient
from    ScreenPrinter import Screen
from    urllib.parse import unquote


class CDPEvent():

    def __init__(self, Message):
    
        self.Message         = Message
        self.Method          = self.Message.get( 'method' )
        self.Result          = self.Message.get( 'result' )
        self.Params          = self.Message.get( 'params' )
        self.Error           = self.Message.get( 'error'  )
        self.Args            = self.Message.get( 'args'   )
        self.CDPObject       = None
        self.DOMEventObjectID = None
        self.DOMEventTargetObjectID = None
        self.DOMEventDetail  = None
        self.DOMEventTargetDetail = None
        self.DataColor       = Style.BRIGHT  + Fore.GREEN   + Back.BLACK
        self.ErrorColor      = Style.BRIGHT  + Fore.RED      + Back.BLACK
        self.LabelColor      = Style.BRIGHT  + Fore.YELLOW    + Back.BLACK
        self.ErrorLabelColor = Style.BRIGHT  + Fore.WHITE    + Back.RED
        self.ResetColor      = Style.RESET_ALL
        
        # This is a CDP package utility function that parses
        # a CDP event string into a CDP object
        
        # fix for one of their bugs:
        if self.Method == 'Animation.animationStarted':
            Animation = self.Params.get('animation')
            if Animation:
                Source = Animation.get('source')
                if Source:
                    Iterations = Source.get('iterations')
                    if Iterations == None:
                        Source['iterations'] = 0
                        
        try:
            self.CDPObject      = cdp.util.parse_json_event( self.Message )
        except BaseException as Failure:
            print( GetExceptionInfo( Failure ))
            os._exit(0)
         
        self.ParseDOMEventSummary()
        self.ParseDOMEventObjects()
        
    
    def ParseDOMEventObjects( self ):

        if type( self.CDPObject ) != cdp.runtime.ConsoleAPICalled:
            return False
            
        if not self.Params: return False
  
        Args = self.Params.get('args')
        
        if ( Args ) and ( len(Args) > 2 ):
            
            self.DOMEventObjectID        = Args[1].get( 'objectId' )
            self.DOMEventTargetObjectID  = Args[2].get( 'objectId' )
            
    
    def GetDOMEventDetails(self, ExecuteMethod, SendCommand ):
        
        if not self.DOMEventDetail:
        
            ObjectID =  cdp.runtime.RemoteObjectId(
                        self.DOMEventObjectID)
                        
            self.DOMEventDetail = ExecuteMethod(
                cdp.runtime.get_properties, 
                object_id = ObjectID,
                own_properties = False,
                accessor_properties_only = False,
                generate_preview = False,
                non_indexed_properties_only = False )
    
            # self.DOMEventDetail.Print()
            
        if not self.DOMEventTargetDetail:

            ObjectID =  cdp.runtime.RemoteObjectId(
                        self.DOMEventTargetObjectID)
                        
            self.DOMEventTargetDetail = ExecuteMethod(
                cdp.runtime.get_properties, 
                object_id = ObjectID,
                own_properties = False,
                accessor_properties_only = False,
                generate_preview = False,
                non_indexed_properties_only = False )
    
            # self.DOMEventTargetDetail.Print()
        
            
    def ParseDOMEventSummary( self ):

        if type( self.CDPObject ) != cdp.runtime.ConsoleAPICalled:
            return False
            
        DOMEvent =  self.Message
        
        if not self.Params: return False
        
        EventItems      = [ 'DOMEventType', 'TargetProto', 'TargetName',
                            'TargetTagName', 'TargetClassName', 
                            'EventMessage', 'EventError', 'TargetText' ]  
        
        for EventItem in EventItems:
        
            EventValue  =  [  PropItem.get      ( 'value'   )
                              if   DOMEvent.get ( 'params'  ) else [ {} ]
                              for  ArgItem      in DOMEvent.get( 'params'  ).get( 'args' )
                              if   ArgItem.get  ( 'preview' )
                              for  PropItem     in ArgItem.get ( 'preview' ).get( 'properties' )
                              if   PropItem.get ( 'name'    )  == EventItem ]
                              
            EventValue  = EventValue[0] if EventValue else ''
            EventValue  = EventValue.strip().replace('\n', '').strip(' ').strip('"')
            EventValue  = re.sub(' +', ' ', EventValue)
            EventValue  = re.sub('\t+', ' ', EventValue)
                
            if (( EventValue == 'undefined' ) or
                ( EventValue == 'null' )):
                EventValue = ''
                
            if EventItem == 'EventMessage' and EventValue:
                EventValue = unquote(EventValue)
                                 
            setattr( self, EventItem, EventValue )
                        
        return True                
    
    def GetCDPEventDetails( self, ExecuteMethod, SendCommand ):
    
        match type(self.CDPObject):
            case cdp.dom.ChildNodeInserted:
                MessageCopy = copy.deepcopy(self.Message)
                self.PrintMessage()
                ParentNodeID = MessageCopy.get('params').get('parentNodeId')
                PreviousNodeID = MessageCopy.get('params').get('previousNodeId')
                NodeID = MessageCopy.get('params').get('node').get('nodeId')
                BackendNodeID = MessageCopy.get('params').get('node').get('backendNodeId')
                
                ReturnValue = ExecuteMethod(
                                  cdp.dom.describe_node,
                                  backend_node_id = cdp.dom.BackendNodeId(ParentNodeID),
                                  depth = -1,
                                  pierce = True )
                ReturnValue.Print()                                  

                ReturnValue = ExecuteMethod(
                                  cdp.dom.describe_node,
                                  backend_node_id = cdp.dom.BackendNodeId(PreviousNodeID),
                                  depth = -1,
                                  pierce = True )
                ReturnValue.Print()
                
                ReturnValue = ExecuteMethod(
                                  cdp.dom.describe_node,
                                  backend_node_id = cdp.dom.BackendNodeId(BackendNodeID),
                                  depth = -1,
                                  pierce = True)
                ReturnValue.Print()
                
                ReturnValue = ExecuteMethod(
                                  cdp.dom.resolve_node,
                                  node_id = cdp.dom.NodeId(ParentNodeID),
                                  #backend_node_id = cdp.dom.BackendNodeId(BackendNodeID),
                                  object_group = 'ABCD')
                ReturnValue.Print()
                
                
    
    
    def PrintObject( self ):
        Output = '\n'
        Output += ( self.LabelColor + "Async Event (CDP Object): " + 
                    self.ResetColor + '\n' )
        Output += ( self.DataColor + str(self.CDPObject) +
                    self.ResetColor + '\n' )
        Output += '\n'
        print( Output, Truncate=None, Decorate=False)
    
    def PrintMessage( self ):
        Output = '\n'
        Output += ( self.LabelColor + "Async Event (JSON Format): " + 
                    self.ResetColor + '\n' )
        Output += ( self.DataColor + 
                    json.dumps( self.Message, indent = 1 ) +
                    self.ResetColor + '\n' )
        Output += '\n'
        print( Output, Truncate=None, Decorate=False)
        
    def PrintEvent( self ):
        
        print(type(self.CDPObject))
        print(self.CDPObject)
        
    def PrintToScreen( self ):
    
        try:
            if not self.OutputScreen:
                return False
            
            if not self.CDPObject:
                return False
            
            if type( self.CDPObject ) == cdp.runtime.ConsoleAPICalled:
                self.OutputScreen.AddWindowItem( Screen.UpperWindow, self )
            else:
                self.OutputScreen.AddWindowItem( Screen.LowerWindow, self )
                
        except BaseException as Failure:
            print( GetExceptionInfo( Failure ))
            os._exit(0)
            
            #OutputStr = ''
            #OutputStr += f'{self.Method}'
            
            #if self.Params:
            #    OutputStr += f': {json.dumps(self.Params)}'
            #else:
            #    OutputStr += f': No additional data'
            
            #if OutputStr:
            #    self.OutputScreen.AddWindowItem( Screen.LowerWindow, OutputStr )
                
    
    def __getstate__( self ):
        CopyState = copy.copy( self.__dict__ )
        if 'OutputScreen' in CopyState:
            del CopyState['OutputScreen']
        return CopyState
        
    def __str__( self ):
        if self.Message:
            return( json.dumps( self.Message ))
    
    def __len__( self ):
        if self.Message:
            return( len( json.dumps( self.Message )))
    
    def __getitem__(self, Index):
        if self.Message:
            return( json.dumps( self.Message )[Index])
    ...
    
    
class CDPReturnValue():

    def __init__( self, Command, Response ):
    
        try:
        
            self.Response   = Response
            self.Command    = Command

            if isinstance( self.Response, ChromeClient.ChromeClientException ):
                self.Response = { 'error' : GetExceptionInfo( 
                                            self.Response.OriginalException ) }
            
            self.ID         = self.Response.get( 'id' )
            self.Method     = self.Response.get( 'method' )
            self.Result     = self.Response.get( 'result' )
            self.Params     = self.Response.get( 'params' )
            self.Error      = self.Response.get( 'error' )
            self.CDPObject  = None
            
            if isinstance(self.Error, ChromeClient.ChromeClientException):
                self.Error = GetExceptionInfo(self.Error.OriginalException)
            
            if self.Result:
                self.ExceptionDetails = self.Result.get( 'exceptionDetails' )
                if self.ExceptionDetails:
                    self.Error = self.ExceptionDetails
                #if self.Result.get('result'):
                #    self.Result = self.Result.get('result')
            
            self.DataColor       = Style.BRIGHT  + Fore.CYAN   + Back.BLACK
            self.ErrorColor      = Style.BRIGHT  + Fore.RED    + Back.BLACK
            self.LabelColor      = Style.BRIGHT  + Fore.WHITE  + Back.BLACK
            self.ErrorLabelColor = Style.BRIGHT  + Fore.WHITE  + Back.RED
            self.ResetColor      = Style.RESET_ALL        

        except BaseException as Failure:
            raise ChromeClient.ChromeClientException(
                    OriginalException = Failure)

    def IsError( self ):
        return True if self.Error != None else False
        
    def PrintObject( self ):
        Output = '\n'
        Output += ( self.LabelColor + "Command Result (CDP Object): " + 
                    self.ResetColor + '\n' )
        Output += ( self.DataColor + str(self.CDPObject) +
                    self.ResetColor + '\n' )
        Output += '\n'
        print( Output, Truncate=None, Decorate=False)
                
    def PrintResponse( self ):
        Output = '\n'
        Output += ( self.LabelColor + "Full Response (JSON): " + 
                    self.ResetColor + '\n' )
        Output += ( self.DataColor + 
                    json.dumps( self.Response, indent = 1 ) +
                    self.ResetColor + '\n' )
        Output += '\n'
        print( Output, Truncate=None, Decorate=False)

    def PrintResult( self ):
        Output = '\n'
        Output += ( self.LabelColor + "Command Result (JSON): " + 
                    self.ResetColor + '\n' )
        Output += ( self.DataColor + 
                    json.dumps( self.Result, indent = 1 ) +
                    self.ResetColor + '\n' )
        Output += '\n'
        print( Output, Truncate=None, Decorate=False)

    def PrintCommand( self ):
        Output = '\n'
        Output += ( self.LabelColor + "Command: " + 
                    self.ResetColor + '\n' )
        Output += ( self.DataColor + 
                    json.dumps( self.Command, indent = 1 ) +
                    self.ResetColor + '\n' )
        Output += '\n'
        print( Output, Truncate=None, Decorate=False)
    
    def PrintError( self ):
        Output = '\n'
        Output += ( self.ErrorLabelColor + "Error Result: " + 
                    self.ResetColor + '\n' )
        Output += ( self.ErrorColor + 
                    json.dumps( self.Error, indent = 1 ) +
                    self.ResetColor + '\n' )
        Output += '\n'
        print( Output, Truncate=None, Decorate=False)
    
    def Print( self ):
        self.PrintCommand()
        if self.Error == None:
            self.PrintResult()
        else:
            self.PrintError()
        
    def __str__( self ):
        if self.Response:
            return( json.dumps( self.Response, indent = 1 ))
    
    def __len__( self ):
        if self.Response:
            return( len( json.dumps( self.Response, indent = 1 )))
    
    def __getitem__(self, Index):
        if self.Response:
            return( json.dumps( self.Response, indent = 1 )[Index])    
    
    
    ...  # end of CDPResult class
    
    
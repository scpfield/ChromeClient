import  sys, os, time, signal, random, json, re, websocket, ssl, cdp, quopri
import  multiprocessing as mp
import  multiprocessing.managers as mpm
from    colorama import Fore, Back, Style, init as colorama_init
from    websocket import ABNF

from    util import *
from    ChromeLauncher import ChromeLauncher
from    CDPDataWrappers import CDPEvent, CDPReturnValue
from    ScreenPrinter import Screen
   
class ChromeClient():

    def __init__( self ):
            
        try:
            self.ChromeProcess          = None
            self.ReaderProcess          = None
            self.EventProcess           = None
            self.WS                     = None
            self.SessionID              = None
            self.BrowserTargetInfo      = None
            self.PageTargetInfo         = None
            self.ReaderReadyEvent       = mp.Event()
            self.SendMutex              = mp.Lock()
            self.MessageID              = mp.Value("i", 0, lock = True)
            self.ChromeLauncher         = ChromeLauncher()
            self.CommandQueue           = mp.Queue()
            self.EventQueue             = mp.Queue()
            # self.EventProcessorStopFlag = mp.Value("b", False, lock = True)
            
            #( self.ReaderCommandPipe, 
            #  self.ClientCommandPipe, ) = mp.Pipe()
            
            #( self.ReaderEventPipe, 
            #  self.ClientEventPipe,   ) = mp.Pipe()
            
            # Hack to switch websocket._abnf lock class 
            # to use the serializable multiprocess class
            websocket._abnf.Lock        = mp.Lock()
            
            # Launch Chrome
            self.ChromeProcess = self.ChromeLauncher.Launch()
            if not self.ChromeProcess:
                raise ChromeClientException("Failed to launch Chrome")
            
            # Get the Browser + Page target info from Chrome's special
            # HTTP URLs which provide the websocket URLs for each
            self.BrowserTargetInfo  = self.ChromeLauncher.GetBrowserTargetInfo()
            self.PageTargetInfo     = self.ChromeLauncher.GetPageTargetInfo()
            
            if (( not self.BrowserTargetInfo )  or
                ( not self.PageTargetInfo    )):
                raise ChromeClientException("Failed to get target info")
            
            # Create Page Session with Chrome
            if not self.CreateSession():
                raise ChromeClientException("Failed to create Chrome sessions")
    
        except BaseException as Failure:
            raise   ChromeClientException( 
                    OriginalException = Failure )
    
        
    def CreateSession( self ):

        print("Creating Chrome Sessions")
    
        try:
            # Connect to the Page websocket URL
            if not self.Connect( 
                URL = self.PageTargetInfo.get('webSocketDebuggerUrl')):
                return False
        
            # Start MessageReader process
            self.ReaderProcess = self.StartMessageReader()
            if not self.ReaderProcess:
                return False
                
            # Execute the CDP command to attach to the Page target
            # and it returns a Page sessionId
            ReturnValue     =   self.ExecuteMethod( 
                                cdp.target.attach_to_target, 
                                target_id = cdp.target.TargetID(
                                    self.PageTargetInfo['id'] ),
                                flatten = True )
            
            ReturnValue.Print()
            self.SessionID  = ReturnValue.CDPObject
            
            if not self.SessionID:
                print("Failed to get SessionID")
                return False
                            
            # Execute CDP command to auto-attach to new Pages
            ReturnValue     =   self.ExecuteMethod(
                                cdp.target.set_auto_attach, 
                                auto_attach = True, 
                                flatten     = True,
                                wait_for_debugger_on_start = False )
           
            # Start EventProcessor process
            self.EventProcess = self.StartEventProcessor()
            if not self.EventProcess:
                return False
                
            return True
            
        except BaseException as Failure:
            raise ChromeClientException( 
                  OriginalException = Failure )
            
        ... # End of CreateSession
                
        
    def Connect( self, URL ):

        SSLOptions = {  'cert_reqs'      : ssl.CERT_NONE, 
                        'check_hostname' : False }
        
        # Creating WebSocket class with multithread=False,
        # because all it does is synchronize calls to 
        # socket.send() using the non-serializable threading.Lock
        # We will synchronize ourselves using mp.Lock

        try:
            self.WS = websocket.WebSocket( 
                        sslopt              = SSLOptions,
                        enable_multithread  = False)

            # Try to connect with short timeout
            # then increase if connected
                        
            self.WS.connect( URL,
                suppress_origin = True,
                timeout = 5 )

            if not self.WS.connected:
                return False        
    
            print( f"Connected To: {URL}" )
            self.WS.settimeout( 20 )
            
            return True
            
        except BaseException as Failure:
            raise ChromeClientException( 
                  OriginalException = Failure )
        

    def ExecuteMethod( self, CDPMethod, **kwargs ):
        
        #print("ExecuteMethod called")
        # The methods from the CDP package accept Python
        # objects that represent the Chrome data models, 
        # and return generators which serializes them to
        # JSON dictionary format for transmission.
        #
        # The way it works is you call the generator twice.
        # First to serialize the full Chrome command.
        # Then a second time to process the response
        # from Chrome by de-serializing back into a Python object.
        # 
        
        # First call the CDP method to get the generator,
        # initializing it with all the args for the call
        Generator       = CDPMethod( **kwargs )
        
        # Next, invoke the generator the first time 
        # which returns a JSON dictionary of the Chrome 
        # method with the args 
        # note:  send(None) is the same as next()
        ChromeMethod    = Generator.send( None )
        
        # Now we send the command to Chrome and wait for response
        # The response is a JSON string, that we load as a JSON
        # dictionary.  Or we get a ChromeClientException.
        
        #print("Sending command: ", ChromeMethod)
        Response        = self.SendCommand( ChromeMethod )
        
        #print("Sent command: ", ChromeMethod)
        # Create a ReturnValue container for the Response
        # which stores the Chrome response in various forms
        ReturnValue     = CDPReturnValue( ChromeMethod, Response )
        
        #print("Return Value: ", ReturnValue)
        if (( ReturnValue.Result != None )  and 
            ( ReturnValue.Error  == None )):
        
            #
            # To convert the JSON dictionary response to a 
            # python CDP object, you call the CDP generator 
            # a second time.  
            #
            # It converts and then delivers the python object
            # by raising a StopIteration which it adds the python 
            # object of the result as an attribute of the Exception 
            # itself. It's kind of weird but that's the way it works.
            #
            
            try:
            
                Generator.send( ReturnValue.Result )
                
                # Note: Some of the CDP return values
                # turn into Tuples after conversion to 
                # Python objects.
                # Sometimes 2, 3 or 4 values depending
                # on the API call.
                
            except StopIteration as ObjectResult:
                ReturnValue.CDPObject = ObjectResult.value
        
        #ReturnValue.Print()
        #ReturnValue.PrintObject()
        return ReturnValue
        ... # End of Execute
    
    
    def __getstate__( self ):
        StateCopy = copy.copy( self.__dict__ )
        if 'ChromeLauncher' in StateCopy:
            del StateCopy['ChromeLauncher']
        if 'ChromeProcess' in StateCopy:
            del StateCopy['ChromeProcess']            
        if 'ReaderProcess' in StateCopy:
            del StateCopy['ReaderProcess']
        if 'EventProcess' in StateCopy:
            del StateCopy['EventProcess']
            
        for k, v in StateCopy.items():
            print(k, ' = ', v)
    
        return StateCopy
    
    def ExecuteScript(  self, 
                        JavaScript, 
                        ReturnByValue          = True, 
                        GenerateWebDriverValue = False ):
    
        ReturnValue = self.ExecuteMethod( 
            cdp.runtime.evaluate,
            expression                        = JavaScript,
            object_group                      = RandomString(10),
            return_by_value                   = ReturnByValue,
            generate_web_driver_value         = GenerateWebDriverValue,
            include_command_line_api          = True,
            silent                            = False,
            generate_preview                  = False,
            user_gesture                      = True,
            await_promise                     = True,
            throw_on_side_effect              = False,
            timeout                           = cdp.runtime.TimeDelta(60000),
            disable_breaks                    = True,
            repl_mode                         = True,
            allow_unsafe_eval_blocked_by_csp  = True )

        return ReturnValue

        
    # Start of execution for the EventProcessor process
    @staticmethod
    def EventProcessor( EventQueue,
                        ExecuteMethod,
                        ExecuteScript,
                        SendCommand ):
        
        print('EventProcessor: Started')
        
        EventMessage                = None
        OutputScreen                = Screen()
        OutputScreen.ExecuteMethod  = ExecuteMethod
        OutputScreen.SendCommand    = SendCommand
        
        try:            
            while True:
            
                if not OutputScreen.ScreenThread.is_alive(): return False
                
                EventMessage  =  CDPEvent( EventQueue.get() )
                EventMessage.OutputScreen = OutputScreen
                
                if not EventMessage.CDPObject:
                    print('ERROR: Missing CDPObject!')
                    EventMessage.PrintMessage()
                    OutputScreen.CloseScreen()
                    os._exit(0)
                    
                match type( EventMessage.CDPObject ):
                                        
                    case cdp.css.MediaQueryResultChanged:
                        if EventMessage.Params:
                            EventMessage.PrintToScreen()
                    
                    case cdp.audits.IssueAdded:
                        EventMessage.PrintToScreen()
                        EventMessage.PrintMessage()
                    
                    case cdp.page.FrameStoppedLoading:

                        EventMessage.PrintToScreen()
                        Result = ExecuteMethod( cdp.dom.get_document,
                                                depth = -1, pierce = True )
                        Result = ExecuteMethod( cdp.dom.request_child_nodes,
                                                node_id = cdp.dom.NodeId( 0 ), 
                                                depth = -1, pierce = True   )                    

                    case cdp.page.LoadEventFired:

                        EventMessage.PrintToScreen()                                        
                        Result = ExecuteMethod( cdp.dom.get_document,
                                                depth = -1, pierce = True )
                        Result = ExecuteMethod( cdp.dom.request_child_nodes,
                                                node_id = cdp.dom.NodeId( 0 ), 
                                                depth = -1, pierce = True   )                        

                    case cdp.page.DomContentEventFired:

                        EventMessage.PrintToScreen()
                        Result = ExecuteMethod( cdp.dom.get_document,
                                                depth = -1, pierce = True )                        
                        Result = ExecuteMethod( cdp.dom.request_child_nodes,
                                                node_id = cdp.dom.NodeId( 0 ), 
                                                depth = -1, pierce = True   )

                    case cdp.accessibility.LoadComplete:
                        EventMessage.PrintToScreen()
                        Result = ExecuteMethod( cdp.dom.get_document,
                                                depth = -1, pierce = True )
                        Result = ExecuteMethod( cdp.dom.request_child_nodes,
                                                node_id = cdp.dom.NodeId( 0 ), 
                                                depth = -1, pierce = True   ) 

                    case cdp.accessibility.NodesUpdated:
                        EventMessage.PrintToScreen()
                        Result = ExecuteMethod( cdp.dom.get_document,
                                                depth = -1, pierce = True )
                        Result = ExecuteMethod( cdp.dom.request_child_nodes,
                                                node_id = cdp.dom.NodeId( 0 ), 
                                                depth = -1, pierce = True   ) 
                    
                    case cdp.dom.ChildNodeInserted:
                        EventMessage.PrintToScreen()
                        Result = ExecuteMethod( cdp.dom.get_document,
                                                depth = -1, pierce = True )
                        Result = ExecuteMethod( cdp.dom.request_child_nodes,
                                                node_id = cdp.dom.NodeId( 0 ), 
                                                depth = -1, pierce = True   )                     
                    
                    case cdp.css.FontsUpdated:
                    
                        if EventMessage.Params:
                            EventMessage.PrintToScreen()
                    
                    case cdp.console.MessageAdded:
                        continue
                        
                    case cdp.fetch.RequestPaused:
                    
                        EventMessage.PrintToScreen()
                        RequestID = EventMessage.CDPObject.request_id
                        
                        Result = ExecuteMethod( cdp.fetch.continue_request,
                                                request_id = RequestID )
                        
                    
                    case cdp.runtime.ConsoleAPICalled:
                        
                        DOMEvent =  EventMessage.Message
                        Excluded =  [ 'mousemove', 'pointermove', 'pointerrawupdate', '' ]

                        #EventMessage.PrintMessage()
                        
                        if not EventMessage.Params: continue
                    
                        if EventMessage.DOMEventType not in Excluded:

                            EventMessage.GetDOMEventDetails( 
                                         ExecuteMethod, 
                                         SendCommand )
                            
                            EventMessage.PrintToScreen()
                                                                    
                    case _:
                        EventMessage.PrintToScreen()
                
        except BaseException as Failure:
            print( GetExceptionInfo( Failure ))
        finally:
            print('EventProcessor exiting')
            #EventMessage.PrintMessage()    
            OutputScreen.CloseScreen()
            os._exit(0)
            
    
    # Start of execution for the MessageReader process
    @staticmethod
    def MessageReader(  WS, 
                        CommandQueue, 
                        EventQueue,
                        ReaderReadyEvent ):
                
        try:
            # Signal the ReadyEvent so clients will know
            ReaderReadyEvent.set()

            # Loop forever or until we are terminated
            while True:
            
                Opcode = Frame = Message = None
                
                # Block until a websocket message arrives
                ( Opcode, 
                  Frame, )  = WS.recv_data( control_frame = False )
            
                # Process new message
                match Opcode:
                
                    case ABNF.OPCODE_TEXT:
                    
                        # Load the text message as a JSON dictionary
                        Message = json.loads( Frame.decode('utf-8') )
            
                        # If there is an 'id' value, it means it is
                        # the result of a CDP function call command.
                        # If not, it is an async CDP event.

                        if Message.get('id') != None:
                        
                            # Send the result to the caller
                            #ReaderCommandPipe.send( Message )
                            CommandQueue.put( Message )

                        else:
                            # Send the event to the event processor
                            #ReaderEventPipe.send( Message )
                            EventQueue.put( Message )

                    # Various other opcodes, not sure what to
                    # do with some of them
                    case ABNF.OPCODE_CONT:
                        print()
                        print( 'Control Frame Received:' )
                        print( Frame )
                        print()
                    case ABNF.OPCODE_BINARY:
                        print()
                        print( 'Binary Frame Received')
                        print()
                    case ABNF.OPCODE_CLOSE:
                        print()
                        print( 'Close Frame Received' )
                        print()
                        raise ChromeClientException("Close Frame Received")
                    case ABNF.OPCODE_PING:
                        print()
                        print( 'Ping Frame Received' )
                        print( Frame )
                        print()
                    case ABNF.OPCODE_PONG:
                        print()
                        print( 'Pong Frame Received' )
                        print( Frame )
                        print()
                    case _:
                        print()
                        print( 'Unknown Opcode Received' )
                        print( Frame )
                        print()
                        raise ChromeClientException("Unknown Frame Received")
        
        except BaseException as Failure:
            ReaderReadyEvent.clear()
            raise SystemExit

            
    def SendCommand( self, Command ):
 
        try:
        
            # The mp.Lock mutex is nice because it supports
            # the context manager which automatically
            # releases the lock even if an exception occurs
            
            # This is blocking call
            #with self.SendMutex:

            # If we got a string, load it as a JSON dict
            # to add the ID and Session values
            if isinstance( Command, str):
                Command = json.loads( Command )
            
            # Each command needs to have a unique ID
            # so we use an incrementing integer value
            Command['id'] = self.MessageID.value

            # The sessionId is optional, but we're using it
            if self.SessionID:
                Command['sessionId'] = self.SessionID
            
            # Now we need to serialize it to a JSON string
            # to send it to Chrome via websocket
            Command = json.dumps( Command )
            
            self.WS.send( Command, opcode = ABNF.OPCODE_TEXT )
            
            # The response arrives asychronously, and is
            # read by the MessagerReader process, which then
            # sends it here via the CommandPipe
            
            # This is blocking call
            #Response = self.ClientCommandPipe.recv()
            Response = self.CommandQueue.get()

            # Increment MessageID counter for the next call
            
            with self.MessageID.get_lock():
                self.MessageID.value += 1

            return Response
        
        except BaseException as Failure:
            return( ChromeClientException( 
                    OriginalException = Failure ))
            
            
    def StartMessageReader( self ):
    
        try:
        
            # Create a MessageReader Process
            # A message-loop for incoming websocket messages
            
            self.ReaderReadyEvent.clear()
            
            ReaderProcess   =   mp.Process(
                                daemon  =   True,
                                target  =   self.MessageReader, 
                                args    = ( self.WS, 
                                            self.CommandQueue,
                                            self.EventQueue,
                                            self.ReaderReadyEvent, ))
            ReaderProcess.start()
            
            # After launching the process, wait for it to
            # give the Ready signal
            self.ReaderReadyEvent.wait()
            return ReaderProcess
            
        except BaseException as Failure:
            raise ChromeClientException(
                  OriginalException = Failure)
   
   
    def StopMessageReader( self ):
        
        if (( self.ReaderProcess) and
            ( self.ReaderProcess.is_alive())):
            
            try:
                self.ReaderProcess.terminate()
                self.ReaderProcess.join()
                self.ReaderReadyEvent.clear()

            except BaseException as ExpectedFailure:
                ...
            

    def StartEventProcessor( self ):
    
        try:
            # Create the Event Processor process.
            # It just loops on receiving events from
            # Chrome via a pipe connection with the 
            # MessageReader, and prints them
            #
            # It also can make outbound calls and
            # all it needs are the class methods 
            # for sending messages.
            EventProcess =  mp.Process(
                            daemon  =   True,
                            target  =   self.EventProcessor, 
                            args    = ( self.EventQueue,
                                        self.ExecuteMethod,
                                        self.ExecuteScript,
                                        self.SendCommand ))
                                
            EventProcess.start()
            return EventProcess
            
        except BaseException as Failure:
            raise  ChromeClientException(
                   OriginalException = Failure)
   
    def StopEventProcessor( self ):
        
        if (( self.EventProcess) and
            ( self.EventProcess.is_alive())):
            
            try:
                self.EventProcess.terminate()
                self.EventProcess.join()                    
            except BaseException as ExpectedFailure:
                ...

    def CloseChrome( self ):
        if  (( self.ChromeProcess   )   and
             ( self.ReaderProcess   )   and
             ( self.WS.connected    )):
                return self.ExecuteMethod( cdp.browser.close )
            
        ... # End of CDPClient class
    

class ChromeClientException( BaseException ):
    def __init__(self, OriginalException = None, *args, **kwargs ):
        super().__init__(*args, **kwargs)
        self.OriginalException = OriginalException


def main():
    print("Hello World")

    
if __name__ == '__main__':
    mp.freeze_support()
    colorama_init( autoreset = False )
    main()


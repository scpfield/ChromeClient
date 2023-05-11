import  sys, os, time, signal, random, json, websocket, ssl, socket, ctypes
import  multiprocessing as mp
import  multiprocessing.managers as mpm
import  multiprocessing.connection as mpc
import  cdp
from    websocket import ABNF
from    ChromeLauncher import ChromeLauncher
from    util import *
from    colorama import Fore, Back, Style, init as colorama_init
from    ChromeClient import *
from    JavaScriptInjections import *



class ChromeClientApp():

    def __init__( self, Config = None ):

        #signal.signal( signal.SIGINT,   self.OSSignalHandler )
        #signal.signal( signal.SIGBREAK, self.OSSignalHandler )
        #signal.signal( signal.SIGABRT,  self.OSSignalHandler )

        self.Client = ChromeClient()


    def AddJavaScriptInjection( self ):
    
        ReturnValue = self.Client.ExecuteMethod( 
                        cdp.page.add_script_to_evaluate_on_new_document,
                        source = AddAllEventsListener, 
                        world_name = None, 
                        include_command_line_api = True)
                        
        ReturnValue.Print()

    def EnableDomains( self ):

        Client = self.Client
        ReturnValue = Client.ExecuteMethod( cdp.log.enable )
        ReturnValue = Client.ExecuteMethod( cdp.page.enable ) 
        
        self.AddJavaScriptInjection()
        
        ReturnValue = Client.ExecuteMethod( cdp.dom.enable )
        ReturnValue = Client.ExecuteMethod( cdp.dom_snapshot.enable )
        ReturnValue = Client.ExecuteMethod( cdp.dom_storage.enable )
        ReturnValue = Client.ExecuteMethod( cdp.debugger.enable )
        ReturnValue = Client.ExecuteMethod( cdp.runtime.enable )
        ReturnValue = Client.ExecuteMethod( cdp.css.enable )
        # ReturnValue = Client.ExecuteMethod( cdp.network.enable )
        # ReturnValue = Client.ExecuteMethod( cdp.fetch.enable )
        ReturnValue = Client.ExecuteMethod( cdp.accessibility.enable )
        ReturnValue = Client.ExecuteMethod( cdp.audits.enable )
        ReturnValue = Client.ExecuteMethod( cdp.inspector.enable )
        ReturnValue = Client.ExecuteMethod( cdp.overlay.enable )
        ReturnValue = Client.ExecuteMethod( cdp.profiler.enable )
        ReturnValue = Client.ExecuteMethod( cdp.performance.enable )
        ReturnValue = Client.ExecuteMethod( cdp.service_worker.enable )
        ReturnValue = Client.ExecuteMethod( cdp.layer_tree.enable )
        ReturnValue = Client.ExecuteMethod( cdp.media.enable )
        ReturnValue = Client.ExecuteMethod( cdp.console.enable )
        ReturnValue = Client.ExecuteMethod( cdp.cast.enable )
        ReturnValue = Client.ExecuteMethod( cdp.database.enable )
        ReturnValue = Client.ExecuteMethod( cdp.animation.enable )
        ReturnValue = Client.ExecuteMethod( cdp.indexed_db.enable )
        ReturnValue = Client.ExecuteMethod( cdp.heap_profiler.enable )
        ReturnValue = Client.ExecuteMethod( cdp.security.enable )
        ReturnValue = Client.ExecuteMethod( cdp.web_authn.enable )

        ReturnValue = Client.ExecuteMethod( cdp.dom.get_document,
                                            depth = -1, pierce = True )
                              
        ReturnValue = Client.ExecuteMethod( cdp.dom.request_child_nodes,
                                            node_id = cdp.dom.NodeId( 0) , 
                                            depth = -1, pierce = True )
                               
        print("Finished Enabling Domains")

    def OSSignalHandler( self, Signal, Frame ):
        try:
        
            print( f'Caught Signal: ' +
                   f'{signal.strsignal(Signal)}' )
                   
            self.Client.CloseChrome()
            
        except SystemExit:
            print('SystemExit')
        except InterruptedError:
            print('InterruptedError')        
        except BaseException as Failure:
            ... # print( GetExceptionInfo(Failure) )
        finally:
            if ClientApp.Client.ChromeProcess:
                ClientApp.Client.CloseChrome()
            os._quit(0)


def main():
        
    try:

        ClientApp = ChromeClientApp()
        
        ClientApp.EnableDomains()

        while ClientApp.Client.EventProcess.is_alive():
            print('Sleeping 1')
            time.sleep(1)
            
        if ClientApp.Client.ChromeProcess:
            ClientApp.Client.CloseChrome()
            
    except BaseException as Failure:
        print( GetExceptionInfo( Failure ) )
                
    print('Exiting')
    

if __name__ == '__main__':
    mp.freeze_support()
    colorama_init( autoreset = False )
    

    
    main()
    

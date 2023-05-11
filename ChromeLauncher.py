import sys, os, subprocess, requests, json

class ChromeLauncher():
    
    def __init__( self, HostName = 'localhost', Port = 9222 ):

        self.HostName       = HostName
        self.Port           = Port
        self.Process        = None
        self.DefaultArgs    = [ f' --high-dpi-support=1',
                                f' --force-device-scale-factor=1.5',
                                f' --remote-debugging-port={Port}',
                                f' --remote-allow-origins=* ',
                                f' --user-data-dir="C:\\temp\\chrome"',
                                f' --ignore-certificate-errors',
                                f' --ignore-urlfetcher-cert-requests',
                                f' --allow-insecure-localhost',
                                f' --enable-automation', 
                                f' --enable-smooth-scrolling',
                                f' --disable-permissions-api',
                                f' --disable-web-security',
                                f' --disable-origin-trial-controlled-blink-features',
                                f' --shared-array-buffer-unrestricted-access-allowed',
                                f' --disable-site-isolation-trials',
                                f' --test-type',
                                f' --use-mock-cert-verifier-for-testing',
                                f' --disable-input-event-activation-protection',
                                f' --browser-test',
                                f' --allow-external-pages',
                                f' --allow-profiles-outside-user-dir',
                                f' --allow-ra-in-dev-mode',
                                f' --allow-running-insecure-content',
                                f' --debug-devtools',
                                f' --enable-blink-test-features',
                                f' --enable-experimental-ui-automation',
                                f' --enable-input',
                                f' --no-self-delete',
                                f' --expose-internals-for-testing', 
                                f' --force-devtools-available',  
                                f' --no-sandbox' ]                      
        ...
            
    def Launch( self ):
        
        Command =     [ 'chrome.exe' ]
        Command.extend( self.DefaultArgs )
        
        try:
            CommandStr = ' '.join( Command )
            print('Launching Chrome: ' + CommandStr )
            self.Process = subprocess.Popen( CommandStr )
            return self.Process
        
        except BaseException as e:
            print(GetExceptionInfo(e))
            return None
        ...

    def GetTargetInfo( self, TargetType = None):
    
        Path = None
        
        match TargetType:
            case 'page'     :   Path = '/json'
            case 'browser'  :   Path = '/json/version'
            case _          :   return None
                
        URL = f'http://{self.HostName}:{self.Port}{Path}'
                        
        print('GetTargetInfo: Making HTTP Request to: ' + URL)                        
        
        try:
        
            Response    =  requests.get( url = URL )
            JSONData    =  None
        
            if not Response.ok:
                print( f'Got bad response code: {Response.code}')
                return None
                
            return Response.json()
                
        except BaseException as e:
            print(GetExceptionInfo(e))
            return None
        ...
    
    def GetPageTargetInfo( self, PageIdx = 0 ):
    
        PageTargets = self.GetTargetInfo('page')
        
        print('Number Of PageTargets: ' + str(len(PageTargets)))
        
        if (( not PageTargets ) or
            ( PageIdx > ( len( PageTargets ) - 1 ))):
                return None
        
        for Item in PageTargets:
            print(json.dumps(Item, indent=1))
            Item['type'] = 'page'
            
        return PageTargets[PageIdx]
        ...
        
    def GetBrowserTargetInfo( self ):
        BrowserTargetInfo = self.GetTargetInfo('browser')
        BrowserTargetInfo['type'] = 'browser'
        print(json.dumps(BrowserTargetInfo, indent=1))
        return BrowserTargetInfo
        ...
    
    ...  # End of ChromeLauncher
    
    

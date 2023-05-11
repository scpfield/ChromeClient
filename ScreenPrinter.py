import sys, os, time, threading, multiprocessing as mp
import curses, curses.ascii
from util import *
import CDPDataWrappers

class Screen():

    # class constants
    MainWindow              = 0
    UpperWindow             = 1
    LowerWindow             = 2
    DetailWindow            = 3
    SplitMode               = 0
    UpperMode               = 1
    LowerMode               = 2
    DetailMode              = 3
    DOMEventDetail          = 1
    DOMEventTargetDetail    = 2


    def __init__( self ):

        self.MainWindow          = None
        self.UpperWindow         = None
        self.LowerWindow         = None
        self.MainInputQueue      = mp.Queue()
        self.UpperInputQueue     = mp.Queue()
        self.LowerInputQueue     = mp.Queue()
        self.DetailInputQueue    = mp.Queue()
        self.DetailDataEvent     = None
        self.DetailDataOutput    = None              
        self.UpperDataQueue      = []
        self.LowerDataQueue      = []
        self.MainWindowMinY      = 0
        self.MainWindowMinX      = 0
        self.MainWindowMaxY      = 0
        self.MainWindowMaxX      = 0
        self.UpperWindowMinY     = 0
        self.UpperWindowMinX     = 0
        self.UpperWindowMaxY     = 0
        self.UpperWindowMaxX     = 0
        self.LowerWindowMinY     = 0
        self.LowerWindowMinX     = 0
        self.LowerWindowMaxY     = 0
        self.LowerWindowMaxX     = 0
        self.UpperVisibleMinIdx  = 0
        self.UpperVisibleMaxIdx  = 0
        self.LowerVisibleMinIdx  = 0
        self.LowerVisibleMaxIdx  = 0
        self.DetailVisibleMinIdx = 0
        self.DetailVisibleMaxIdx = 0        
        self.UpperSelectedLine   = None
        self.LowerSelectedLine   = None
        self.SelectedWindow      = Screen.MainWindow
        self.Mode                = Screen.SplitMode
        self.PreviousMode        = Screen.SplitMode 
        self.PreviousWindow      = Screen.MainWindow
        self.DOMDetailType       = Screen.DOMEventDetail
        self.ThreadStopFlag      = False
        self.Paused              = False        
        self.ScreenThread        = threading.Thread(
                                   target  = self.ScreenProcessor,
                                   args    = () )
        self.ScreenThread.start()


    def InitializeCurses( self ):

        # Info(curses)
        
        if not self.MainWindow:
            self.MainWindow           = curses.initscr()
            curses.resize_term        ( curses.LINES, curses.COLS )
            curses.start_color        ()
            curses.use_default_colors ()
        
        curses.update_lines_cols    ()
        curses.noecho               ()
        curses.curs_set             (  0  )
        curses.cbreak               ( False )
        curses.meta                 ( True )
        curses.mousemask            ( curses.REPORT_MOUSE_POSITION |
                                      curses.ALL_MOUSE_EVENTS )
        curses.mouseinterval        ( 50  )


    def PrintSizes( self ):

        SizeAdjust = 0
        if self.MainWindowMaxY % 2 == 0: SizeAdjust = 1
        print()
        print( f'SizeAdjust     = {SizeAdjust}')
        print()
        print( f'MainWindowMinY = {self.MainWindowMinY}' )
        print( f'MainWindowMinX = {self.MainWindowMinX}' )
        print( f'MainWindowMaxY = {self.MainWindowMaxY}' )
        print( f'MainWindowMaxX = {self.MainWindowMaxX}' )
        print()
        print( f'UpperWindowMinY = {self.UpperWindowMinY}' )
        print( f'UpperWindowMinX = {self.UpperWindowMinX}' )
        print( f'UpperWindowMaxY = {self.UpperWindowMaxY}' )
        print( f'UpperWindowMaxX = {self.UpperWindowMaxX}' )
        print()
        print( f'LowerWindowMinY = {self.LowerWindowMinY}' )
        print( f'LowerWindowMinX = {self.LowerWindowMinX}' )
        print( f'LowerWindowMaxY = {self.LowerWindowMaxY}' )
        print( f'LowerWindowMaxX = {self.LowerWindowMaxX}' )

    def InitializeWindows( self ):

        self.MainWindow.leaveok     ( True )
        self.MainWindow.scrollok    ( False )
        self.MainWindow.idlok       ( True )
        self.MainWindow.keypad      ( True )
        self.MainWindow.nodelay     ( True )

        self.UpperWindow.leaveok    ( True )
        self.UpperWindow.scrollok   ( True )
        self.UpperWindow.idlok      ( True )
        self.UpperWindow.keypad     ( True )
        self.UpperWindow.nodelay    ( True )

        self.LowerWindow.leaveok    ( True )
        self.LowerWindow.scrollok   ( True )
        self.LowerWindow.idlok      ( True )
        self.LowerWindow.keypad     ( True )
        self.LowerWindow.nodelay    ( True )

    
    def CreateWindows( self ):

        ( self.MainWindowMinY,
          self.MainWindowMinX, )  = self.MainWindow.getbegyx()

        ( self.MainWindowMaxY,
          self.MainWindowMaxX, )  = self.MainWindow.getmaxyx()

        self.MainWindow.bkgd( ' ', curses.color_pair(
                                   Screen.WHITE_ON_BLACK ))

        self.MainWindow.refresh()
        self.PrintMenu()

        SizeAdjust = 0
        if self.MainWindowMaxY % 2 == 0: SizeAdjust = 1

        self.UpperWindow = curses.newwin(
            ( self.MainWindowMaxY // 2 ) - SizeAdjust,
            ( self.MainWindowMaxX - 1  ), 0, 0 )

        ( self.UpperWindowMinY,
          self.UpperWindowMinX, )  = self.UpperWindow.getbegyx()

        ( self.UpperWindowMaxY,
          self.UpperWindowMaxX, )  = self.UpperWindow.getmaxyx()

        self.UpperWindow.bkgd( ' ', curses.color_pair(
                                    Screen.WHITE_ON_MEDIUM_BLUE ))
        self.UpperWindow.refresh()

        self.LowerWindow = curses.newwin(
            ( self.MainWindowMaxY // 2 ),
              self.MainWindowMaxX - 1,
              self.UpperWindowMaxY, 0  )

        ( self.LowerWindowMinY,
          self.LowerWindowMinX, )  = self.LowerWindow.getbegyx()

        ( self.LowerWindowMaxY,
          self.LowerWindowMaxX, )  = self.LowerWindow.getmaxyx()

        self.LowerWindow.bkgd( ' ', curses.color_pair(
                                    Screen.YELLOW_ON_MEDIUM_GREEN ))
        self.LowerWindow.refresh()


    def CloseScreen( self ):
        self.ThreadStopFlag = True

    def AddWindowItem( self, WindowID, Data ):

        if not self.ScreenThread.is_alive():
            return False

        match WindowID:
            case Screen.MainWindow:
                self.MainInputQueue.put( Data,  block = False )
                return True
            case Screen.UpperWindow:
                self.UpperInputQueue.put( Data, block = False )
                return True
            case Screen.LowerWindow:
                self.LowerInputQueue.put( Data, block = False )
                return True
            case _:
                print('Unknown WindowID')
                return False

    def GetWindowItems( self, WindowID ):

        Items = []
        match WindowID:
            case Screen.MainWindow:
                while not self.MainInputQueue.empty():
                    Items.append(
                        self.MainInputQueue.get( block = False ))
            case Screen.UpperWindow:
                while not self.UpperInputQueue.empty():
                    Items.append(
                        self.UpperInputQueue.get( block = False ))
                self.UpperDataQueue.extend( Items )
            case Screen.LowerWindow:
                while not self.LowerInputQueue.empty():
                    Items.append(
                        self.LowerInputQueue.get( block = False ))
                self.LowerDataQueue.extend( Items )

        return Items


    def ScreenProcessor( self ):
    
        curses.use_env          ( True )
        curses.setupterm        ()
        self.InitializeCurses   ()
        self.InitializeColors   ()
        self.CreateWindows      ()
        self.InitializeWindows  ()
        self.Paused             = False

        print('ScreenProcessor: Started')

        while not self.ThreadStopFlag:

            try:

                time.sleep(0.05)

                if self.Mode in [ Screen.SplitMode, 
                                  Screen.UpperMode, 
                                  Screen.LowerMode ]:
                                  
                    MainItems  = self.GetWindowItems( Screen.MainWindow  )
                    for Item in MainItems:
                        self.Print( Screen.MainWindow, Item  )

                if not self.Paused:

                    if self.Mode in [ Screen.SplitMode, 
                                      Screen.UpperMode ]:
                                      
                        UpperItems = self.GetWindowItems( Screen.UpperWindow )
                        for Item in UpperItems:
                            self.Print( Screen.UpperWindow, Item )

                    if self.Mode in [ Screen.SplitMode, 
                                      Screen.LowerMode ]:
                                      
                        LowerItems = self.GetWindowItems( Screen.LowerWindow )
                        for Item in LowerItems:
                            self.Print( Screen.LowerWindow, Item )


                Key = self.MainWindow.getch()
                #print("Got Key: ", Key)
                
                if (( Key == ord('q')) or
                    ( Key == ord('Q'))):
                        self.ThreadStopFlag = True

                if (( Key == ord('p')) or
                    ( Key == ord('P'))):
                        self.Paused = True
                        self.PrintMenu()

                if (( Key == ord('r')) or
                    ( Key == ord('R'))):
                        self.Paused = False
                        self.PrintMenu()

                if (( Key == ord('m')) or
                    ( Key == ord('M'))):
                        self.SwitchModes()
                        
                if (( Key == ord('c')) or
                    ( Key == ord('C'))):
                        ...

                if (( Key == ord('e')) or
                    ( Key == ord('E'))):
                        if self.Mode == Screen.DetailMode:
                            if self.PreviousWindow == Screen.UpperWindow:
                                self.DOMDetailType = Screen.DOMEventDetail
                                self.PrintEventDetail( 
                                    self.DetailDataEvent,
                                    DOMDetailType = Screen.DOMEventDetail)
                                
                if (( Key == ord('t')) or
                    ( Key == ord('T'))):
                        if self.Mode == Screen.DetailMode:
                            if self.PreviousWindow == Screen.UpperWindow:
                                self.DOMDetailType = Screen.DOMEventTargetDetail
                                self.PrintEventDetail( 
                                    self.DetailDataEvent,
                                    DOMDetailType = Screen.DOMEventTargetDetail)
                                                       

                if Key in [ #curses.KEY_ENTER, 
                            curses.ascii.CR ]: 
                            #curses.PADENTER ]:
                
                    if self.Mode in [ Screen.SplitMode,
                                      Screen.UpperMode,
                                      Screen.LowerMode ]:
                    
                        self.DetailDataEvent  = None
                        self.DetailDataOutput = None
                        
                        if (( self.SelectedWindow == Screen.UpperWindow ) and
                            ( self.UpperSelectedLine != None )):
                                self.DetailDataEvent = (
                                    self.UpperDataQueue[
                                    self.UpperVisibleMinIdx + self.UpperSelectedLine ])
                    
                        if (( self.SelectedWindow == Screen.LowerWindow ) and
                            ( self.LowerSelectedLine != None )):
                                self.DetailDataEvent = (
                                    self.LowerDataQueue[
                                    self.LowerVisibleMinIdx + self.LowerSelectedLine ])

                        if self.DetailDataEvent:
                            self.PreviousMode   = self.Mode
                            self.PreviousWindow = self.SelectedWindow
                            self.SelectedWindow = Screen.MainWindow
                            self.Mode           = Screen.DetailMode
                            self.MainWindow.move( 0, 0 )
                            self.MainWindow.clear()
                            self.Print( Screen.MainWindow, self.DetailDataEvent )
                            self.PrintMenu()
                    
                
                if Key == curses.ascii.ESC:
                    self.LowerWindow.redrawwin()
                    self.UpperWindow.redrawwin()
                    self.LowerWindow.refresh()
                    self.UpperWindow.refresh()
                    self.SelectedWindow = self.PreviousWindow
                    self.SwitchModes( TargetMode = self.PreviousMode )
                    self.PrintMenu()

                if Key == curses.KEY_RESIZE:
                    match self.Mode:
                        case Screen.SplitMode:
                            self.ResizeSplitMode()
                        case Screen.UpperMode:
                            self.ResizeUpperMode()
                        case Screen.LowerMode:
                            self.ResizeLowerMode()
                        case Screen.DetailMode:
                            self.ResizeDetailMode()                            

                if Key == curses.KEY_UP:

                    # Handle the main window detail output
                    if self.SelectedWindow == Screen.MainWindow:
                        CurrentY, CurrentX = self.MainWindow.getyx()
            
                        if self.DetailVisibleMinIdx == 0:
                            continue
                        
                        if self.DetailVisibleMinIdx > 0:
                              
                            self.DetailVisibleMinIdx -= 1
                            self.DetailVisibleMaxIdx -= 1
                            self.PrintEventDetail( 
                                self.DetailDataEvent, 
                                DetailMinIdx = self.DetailVisibleMinIdx,
                                DetailMaxIdx = self.DetailVisibleMaxIdx,
                                DOMDetailType = self.DOMDetailType )
                            

                    # Handle the upper window
                    if self.SelectedWindow == Screen.UpperWindow:
                        CurrentY, CurrentX = self.UpperWindow.getyx()
                        
                        # No lines are currently selected, no need to do anything
                        if self.UpperSelectedLine == None:
                            continue

                        # If we are at the top of the list and nothing more available
                        if (( self.UpperSelectedLine  == 0 ) and
                            ( self.UpperVisibleMinIdx == 0 )):
                                continue

                        # If we are at the top of the list and there is more available
                        if (( self.UpperSelectedLine  == 0 ) and
                            ( self.UpperVisibleMinIdx > 0 )):
                            
                                self.UpperVisibleMinIdx -= 1
                                self.UpperVisibleMaxIdx -= 1
                                self.UpperWindow.move( 0, 0)
                                self.UpperWindow.insertln()
                                Data = self.UpperDataQueue[self.UpperVisibleMinIdx]
                                self.PrintDOMEvent( Data, Selected = True, NewData = False )
                                self.PrevSelectedLine = self.UpperSelectedLine + 1
                                PrevSelectedData = self.UpperDataQueue[self.UpperVisibleMinIdx + 1]
                                self.UpperWindow.move( self.PrevSelectedLine, 0 )
                                self.PrintDOMEvent( PrevSelectedData, Selected = False, NewData = False )
                                self.UpperSelectedLine = 0
                                self.UpperWindow.move( CurrentY, CurrentX )
                                self.UpperWindow.refresh()
                                self.SelectedWindow = Screen.UpperWindow
                                continue

                        # If we are not at the top of the list
                        self.PrevSelectedLine = self.UpperSelectedLine
                        PrevSelectedData = self.UpperDataQueue[self.UpperVisibleMinIdx + self.PrevSelectedLine]
                        self.UpperWindow.move( self.PrevSelectedLine, 0 )
                        self.PrintDOMEvent( PrevSelectedData, Selected = False, NewData = False )
                        self.UpperSelectedLine -= 1
                        Data = self.UpperDataQueue[self.UpperVisibleMinIdx + self.UpperSelectedLine]
                        self.UpperWindow.move( self.UpperSelectedLine, 0 )
                        self.PrintDOMEvent( Data, Selected = True, NewData = False )
                        self.UpperWindow.move( CurrentY, CurrentX )
                        self.UpperWindow.refresh()
                        self.SelectedWindow = Screen.UpperWindow
                        continue

                    # Handle the lower window
                    if self.SelectedWindow == Screen.LowerWindow:
                        CurrentY, CurrentX = self.LowerWindow.getyx()
                        
                        # No lines are currently selected, no need to do anything
                        if self.LowerSelectedLine == None:
                            continue

                        # If we are at the top of the list and nothing more available
                        if (( self.LowerSelectedLine  == 0 ) and
                            ( self.LowerVisibleMinIdx == 0 )):
                                continue

                        # If we are at the top of the list and there is more available
                        if (( self.LowerSelectedLine  == 0 ) and
                            ( self.LowerVisibleMinIdx > 0 )):
                            
                                self.LowerVisibleMinIdx -= 1
                                self.LowerVisibleMaxIdx -= 1
                                self.LowerWindow.move( 0, 0)
                                self.LowerWindow.insertln()
                                Data = self.LowerDataQueue[self.LowerVisibleMinIdx]
                                self.PrintCDPEvent( Data, Selected = True, NewData = False )
                                self.PrevSelectedLine = self.LowerSelectedLine + 1
                                PrevSelectedData = self.LowerDataQueue[self.LowerVisibleMinIdx + 1]
                                self.LowerWindow.move( self.PrevSelectedLine, 0 )
                                self.PrintCDPEvent( PrevSelectedData, Selected = False, NewData = False )
                                self.LowerSelectedLine = 0
                                self.LowerWindow.move( CurrentY, CurrentX )
                                self.LowerWindow.refresh()
                                self.SelectedWindow = Screen.LowerWindow
                                continue

                        # If we are not at the top of the list
                        self.PrevSelectedLine = self.LowerSelectedLine
                        PrevSelectedData = self.LowerDataQueue[self.LowerVisibleMinIdx + self.PrevSelectedLine]
                        self.LowerWindow.move( self.PrevSelectedLine, 0 )
                        self.PrintCDPEvent( PrevSelectedData, Selected = False, NewData = False )
                        self.LowerSelectedLine -= 1
                        Data = self.LowerDataQueue[self.LowerVisibleMinIdx + self.LowerSelectedLine]
                        self.LowerWindow.move( self.LowerSelectedLine, 0 )
                        self.PrintCDPEvent( Data, Selected = True, NewData = False )
                        self.LowerWindow.move( CurrentY, CurrentX )
                        self.LowerWindow.refresh()
                        self.SelectedWindow = Screen.LowerWindow
                        continue


                if Key == curses.KEY_DOWN:
                    
                    # Handle the main window detail output
                    if self.SelectedWindow == Screen.MainWindow:
                        CurrentY, CurrentX = self.MainWindow.getyx()
            
                        if self.DetailVisibleMaxIdx == len(self.DetailDataOutput):
                            continue
                        
                        if (( self.DetailVisibleMaxIdx < ( len( self.DetailDataOutput ) ) and
                            ( self.DetailVisibleMinIdx + (self.MainWindowMaxY - 1 ) < ( len( self.DetailDataOutput ))))):
                            
                                self.DetailVisibleMinIdx += 1
                                self.DetailVisibleMaxIdx += 1
    
                                self.PrintEventDetail( 
                                    self.DetailDataEvent, 
                                    DetailMinIdx = self.DetailVisibleMinIdx,
                                    DetailMaxIdx = self.DetailVisibleMaxIdx,
                                    DOMDetailType = self.DOMDetailType )

                    # Handle the upper window
                    if self.SelectedWindow == Screen.UpperWindow:
                        CurrentY, CurrentX = self.UpperWindow.getyx()
                        
                        # No lines are currently selected, no need to do anything
                        if self.UpperSelectedLine == None:
                            continue

                        # If we are at the bottom of the list and nothing more available
                        if (( self.UpperSelectedLine  == (self.UpperWindowMaxY - 1 )) and
                            ( self.UpperVisibleMaxIdx == (len(self.UpperDataQueue) - 1))):
                                continue

                        # If we are at the bottom of the list and there is more available
                        if (( self.UpperSelectedLine  == (self.UpperWindowMaxY - 1 ) and
                            ( self.UpperVisibleMaxIdx < (len(self.UpperDataQueue))))):
                            
                                self.UpperVisibleMinIdx += 1
                                self.UpperVisibleMaxIdx += 1
                                self.UpperWindow.move( (self.UpperWindowMaxY - 1), 0)
                                self.UpperWindow.scroll()
                                self.PrevSelectedLine = self.UpperSelectedLine - 1
                                PrevSelectedData = self.UpperDataQueue[self.UpperVisibleMaxIdx - 1]
                                self.UpperWindow.move( self.PrevSelectedLine, 0 )
                                self.PrintDOMEvent( PrevSelectedData, Selected = False, NewData = False )
                                Data = self.UpperDataQueue[self.UpperVisibleMaxIdx]
                                self.UpperSelectedLine = self.UpperWindowMaxY - 1
                                self.UpperWindow.move( self.UpperSelectedLine, 0 )
                                self.PrintDOMEvent( Data, Selected = True, NewData = False )
                                self.UpperWindow.move( CurrentY, CurrentX )
                                self.UpperWindow.refresh()
                                self.SelectedWindow = Screen.UpperWindow
                                continue

                        # If we are not at the bottom of the list
                        NextLineData = self.UpperWindow.instr(
                            ( self.UpperSelectedLine + 1 ), 0 ).decode('utf-8').strip()
                            
                        if not NextLineData: continue
                        self.PrevSelectedLine = self.UpperSelectedLine
                        PrevSelectedData = self.UpperDataQueue[self.UpperVisibleMinIdx + self.PrevSelectedLine]
                        self.UpperWindow.move( self.PrevSelectedLine, 0 )
                        self.PrintDOMEvent( PrevSelectedData, Selected = False, NewData = False )
                        self.UpperSelectedLine += 1
                        Data = self.UpperDataQueue[self.UpperVisibleMinIdx + self.UpperSelectedLine]
                        self.UpperWindow.move( self.UpperSelectedLine, 0 )
                        self.PrintDOMEvent( Data, Selected = True, NewData = False )
                        self.UpperWindow.move( CurrentY, CurrentX )
                        self.UpperWindow.refresh()
                        self.SelectedWindow = Screen.UpperWindow
                        continue

                    # Handle the lower window
                    if self.SelectedWindow == Screen.LowerWindow:
                        CurrentY, CurrentX = self.LowerWindow.getyx()
                        
                        # No lines are currently selected, no need to do anything
                        if self.LowerSelectedLine == None:
                            continue

                        # If we are at the bottom of the list and nothing more available
                        if (( self.LowerSelectedLine  == (self.LowerWindowMaxY - 1 )) and
                            ( self.LowerVisibleMaxIdx == (len(self.LowerDataQueue) - 1))):
                                continue

                        # If we are at the bottom of the list and there is more available
                        if (( self.LowerSelectedLine  == (self.LowerWindowMaxY - 1 ) and
                            ( self.LowerVisibleMaxIdx < (len(self.LowerDataQueue))))):
                            
                                self.LowerVisibleMinIdx += 1
                                self.LowerVisibleMaxIdx += 1
                                self.LowerWindow.move( (self.LowerWindowMaxY - 1), 0)
                                self.LowerWindow.scroll()
                                self.PrevSelectedLine = self.LowerSelectedLine - 1
                                PrevSelectedData = self.LowerDataQueue[self.LowerVisibleMaxIdx - 1]
                                self.LowerWindow.move( self.PrevSelectedLine, 0 )
                                self.PrintCDPEvent( PrevSelectedData, Selected = False, NewData = False )
                                Data = self.LowerDataQueue[self.LowerVisibleMaxIdx]
                                self.LowerSelectedLine = self.LowerWindowMaxY - 1
                                self.LowerWindow.move( self.LowerSelectedLine, 0 )
                                self.PrintCDPEvent( Data, Selected = True, NewData = False )
                                self.LowerWindow.move( CurrentY, CurrentX )
                                self.LowerWindow.refresh()
                                self.SelectedWindow = Screen.LowerWindow
                                continue

                        # If we are not at the bottom of the list
                        NextLineData = self.LowerWindow.instr(
                            ( self.LowerSelectedLine + 1 ), 0 ).decode('utf-8').strip()
                        if not NextLineData: continue
                        self.PrevSelectedLine = self.LowerSelectedLine
                        PrevSelectedData = self.LowerDataQueue[self.LowerVisibleMinIdx + self.PrevSelectedLine]
                        self.LowerWindow.move( self.PrevSelectedLine, 0 )
                        self.PrintCDPEvent( PrevSelectedData, Selected = False, NewData = False )
                        self.LowerSelectedLine += 1
                        Data = self.LowerDataQueue[self.LowerVisibleMinIdx + self.LowerSelectedLine]
                        self.LowerWindow.move( self.LowerSelectedLine, 0 )
                        self.PrintCDPEvent( Data, Selected = True, NewData = False )
                        self.LowerWindow.move( CurrentY, CurrentX )
                        self.LowerWindow.refresh()
                        self.SelectedWindow = Screen.LowerWindow
                        continue


                if Key == curses.KEY_MOUSE:

                    ( MouseID, MouseX, MouseY,
                      MouseZ,  MouseState, )    = curses.getmouse()

                    if MouseState in [ curses.BUTTON1_CLICKED,
                                       curses.BUTTON1_PRESSED ]:
                        
                        if self.Mode in [ Screen.SplitMode, 
                                          Screen.UpperMode ]:
                        
                            if self.UpperWindow.enclose( MouseY, MouseX ):
                                CurrentY, CurrentX = self.UpperWindow.getyx()
                                ClickedLineData = self.UpperWindow.instr(
                                    MouseY - self.UpperWindowMinY, 0).decode('utf-8').strip()
                                if not ClickedLineData: continue
                                if self.UpperSelectedLine != None:
                                    self.PrevSelectedLine = self.UpperSelectedLine
                                    PrevSelectedData = self.UpperDataQueue[self.UpperVisibleMinIdx + self.PrevSelectedLine]
                                    self.UpperWindow.move(self.PrevSelectedLine, 0)
                                    self.PrintDOMEvent( PrevSelectedData, Selected = False, NewData = False )
                                self.UpperSelectedLine = MouseY - self.UpperWindowMinY
                                Data = self.UpperDataQueue[self.UpperVisibleMinIdx + self.UpperSelectedLine]
                                self.UpperWindow.move( self.UpperSelectedLine, 0 )
                                self.PrintDOMEvent( Data, Selected = True, NewData = False )
                                self.UpperWindow.move( CurrentY, CurrentX )
                                self.UpperWindow.refresh()
                                self.PreviousWindow = self.SelectedWindow
                                self.SelectedWindow = Screen.UpperWindow
                                continue

                        if self.Mode in [ Screen.SplitMode, 
                                          Screen.LowerMode ]:
                                          
                            if self.LowerWindow.enclose( MouseY, MouseX ):
                                CurrentY, CurrentX = self.LowerWindow.getyx()
                                ClickedLineData = self.LowerWindow.instr(
                                    MouseY - self.LowerWindowMinY, 0).decode('utf-8').strip()
                                if not ClickedLineData: continue
                                if self.LowerSelectedLine != None:
                                    self.PrevSelectedLine = self.LowerSelectedLine
                                    PrevSelectedData = self.LowerDataQueue[self.LowerVisibleMinIdx + self.PrevSelectedLine]
                                    self.LowerWindow.move(self.PrevSelectedLine, 0)
                                    self.PrintCDPEvent( PrevSelectedData, Selected = False, NewData = False )
                                self.LowerSelectedLine = MouseY - self.LowerWindowMinY
                                Data = self.LowerDataQueue[self.LowerVisibleMinIdx + self.LowerSelectedLine]
                                self.LowerWindow.move( self.LowerSelectedLine, 0 )
                                self.PrintCDPEvent( Data, Selected = True, NewData = False )
                                self.LowerWindow.move( CurrentY, CurrentX )
                                self.LowerWindow.refresh()
                                self.PreviousWindow = self.SelectedWindow
                                self.SelectedWindow = Screen.LowerWindow
                                continue
                                

                        
                    if MouseState == curses.BUTTON1_DOUBLE_CLICKED:

                        self.DetailDataEvent  = None
                        self.DetailDataOutput = None
                        
                        if self.Mode in [ Screen.SplitMode, 
                                          Screen.UpperMode ]:
                                          
                            if self.UpperWindow.enclose( MouseY, MouseX ):
                                CurrentY, CurrentX = self.UpperWindow.getyx()
                                self.UpperSelectedLine = MouseY - self.UpperWindowMinY
                                self.UpperWindow.move( self.UpperSelectedLine, 0 )
                                self.DetailDataEvent = self.UpperDataQueue[self.UpperVisibleMinIdx + self.UpperSelectedLine]

                        if self.Mode in [ Screen.SplitMode, 
                                          Screen.LowerMode ]:
                                          
                            if self.LowerWindow.enclose( MouseY, MouseX ):
                                CurrentY, CurrentX = self.LowerWindow.getyx()
                                self.LowerSelectedLine = MouseY - self.LowerWindowMinY
                                self.LowerWindow.move( self.LowerSelectedLine, 0 )
                                self.DetailDataEvent = self.LowerDataQueue[self.LowerVisibleMinIdx + self.LowerSelectedLine]
                                
                        if self.DetailDataEvent:
                            self.PreviousMode   = self.Mode
                            self.PreviousWindow = self.SelectedWindow
                            self.SelectedWindow = Screen.MainWindow
                            self.Mode           = Screen.DetailMode
                            self.MainWindow.move( 0, 0 )
                            self.MainWindow.clear()
                            self.Print( Screen.MainWindow, self.DetailDataEvent )
                            self.PrintMenu()
                            
                        continue
                        

            except BaseException as PossibleError:
                print( GetExceptionInfo(PossibleError ))
                os._exit(1)
                break

        print("ThreadStopFlag is set, exiting")
        curses.endwin()
        raise SystemExit
        #os._exit(0)
        return True


    def SwitchModes( self, TargetMode = None ):

        print("Current Mode: ", self.Mode)
        self.PreviousMode = self.Mode

        if not TargetMode:
            if self.Mode < 2:
                self.Mode += 1
            else:
                self.Mode = 0
        else:
            self.Mode = TargetMode

        print("New Mode: ", self.Mode)

        match self.Mode:

            case Screen.SplitMode:
                print('ResizeSplitMode')
                self.ResizeSplitMode()

            case Screen.UpperMode:
                print('ResizeUpperMode')
                self.ResizeUpperMode()

            case Screen.LowerMode:
                print('ResizeLowerMode')
                self.ResizeLowerMode()
            
            case Screen.DetailMode:
                print('DetailMode')
                self.ResizeDetailMode()
                
            case _:
                print('Unknown mode')

        ( self.MainWindowMinY,
          self.MainWindowMinX, )    = self.MainWindow.getbegyx()

        ( self.MainWindowMaxY,
          self.MainWindowMaxX, )    = self.MainWindow.getmaxyx()

        ( self.UpperWindowMinY,
          self.UpperWindowMinX, )   = self.UpperWindow.getbegyx()

        ( self.UpperWindowMaxY,
          self.UpperWindowMaxX, )   = self.UpperWindow.getmaxyx()

        ( self.LowerWindowMinY,
          self.LowerWindowMinX, )   = self.LowerWindow.getbegyx()

        ( self.LowerWindowMaxY,
          self.LowerWindowMaxX, )   = self.LowerWindow.getmaxyx()

    def PrintMenu( self, Menu = None ):

        if not Menu:
            if self.Mode == Screen.DetailMode:
                Menu = 'ESC=Return | '
                if self.PreviousWindow == Screen.UpperWindow:
                    Menu += 'E=EventDetail | T=TargetDetail '
            else:
                Menu = 'Q=Quit | M=Mode | P=Pause | R=Resume | '

        self.MainWindow.attron( 
            curses.color_pair( Screen.WHITE_ON_BLACK ) | curses.A_REVERSE )
        
        self.MainWindow.move( self.MainWindowMaxY - 1, 0 )
        self.MainWindow.clrtoeol()
        
        self.MainWindow.addstr( Menu )
        self.MainWindow.addch( curses.ACS_UARROW )
        self.MainWindow.addch( curses.ACS_DARROW )
        self.MainWindow.addstr( '=Scroll')
        
        if self.Mode != Screen.DetailMode:
            self.MainWindow.addstr( ' | ' )
            self.MainWindow.addch( curses.ACS_LARROW )
            self.MainWindow.addch( curses.ACS_LRCORNER )
            self.MainWindow.addstr( '=Detail ' )
        
        if self.Paused:
            ColorPair = curses.color_pair(
                         Screen.RED_ON_BLACK | curses.A_REVERSE )
            self.MainWindow.addstr( ' | ' )
            self.MainWindow.addstr( '[ PAUSED ]', ColorPair )        
        
        self.MainWindow.move( self.MainWindowMaxY - 1, 0 )
        
        MenuLength = len(self.MainWindow.instr().decode( 'utf-8' ).strip())
        Remaining = ( self.MainWindowMaxX - 1 ) - MenuLength
        Blank = ( ' ' * Remaining )
        
        self.MainWindow.move( self.MainWindowMaxY - 1, MenuLength )
        self.MainWindow.addstr( Blank )

        self.MainWindow.attroff( 
            curses.color_pair( Screen.WHITE_ON_PURPLE ))
        
        self.MainWindow.refresh()


    def ResizeUpperMode( self ):

        self.InitializeCurses()
        self.InitializeWindows()

        try:
            ( self.MainWindowMinY,
              self.MainWindowMinX, )  = self.MainWindow.getbegyx()

            ( self.MainWindowMaxY,
              self.MainWindowMaxX, )  = self.MainWindow.getmaxyx()
            
            self.UpperWindow.resize(  self.MainWindowMaxY - 1,
                                      self.MainWindowMaxX - 1 )

            self.UpperWindow.mvwin( 0, 0 )

            ( self.UpperWindowMinY,
              self.UpperWindowMinX, )  = self.UpperWindow.getbegyx()

            ( self.UpperWindowMaxY,
              self.UpperWindowMaxX, )  = self.UpperWindow.getmaxyx()

            ( self.LowerWindowMinY,
              self.LowerWindowMinX, )  = self.LowerWindow.getbegyx()

            ( self.LowerWindowMaxY,
              self.LowerWindowMaxX, )  = self.LowerWindow.getmaxyx()

            self.UpperWindow.bkgd( ' ', curses.color_pair(
                                        Screen.WHITE_ON_MEDIUM_BLUE ))

            self.UpperWindow.refresh()
            self.SelectedWindow = Screen.UpperWindow

            for Line in range( 0, self.UpperWindowMaxY ):
        
                LineData = self.UpperWindow.instr(
                    ( Line ), 0 ).decode( 'utf-8' ).strip()
                                            
                if not LineData:
                    
                    if self.UpperVisibleMaxIdx < ( len(self.UpperDataQueue) - 1 ):
                        self.UpperVisibleMaxIdx += 1
                        Data = self.UpperDataQueue[self.UpperVisibleMaxIdx]
                        self.UpperWindow.move( Line, 0)
                        self.PrintDOMEvent(Data, NewData = False)
                    else:
                        if self.UpperVisibleMinIdx > 0:
                            self.UpperWindow.move( 0, 0)
                            self.UpperWindow.insertln()
                            self.UpperVisibleMinIdx -= 1
                            Data = self.UpperDataQueue[self.UpperVisibleMinIdx]
                            self.PrintDOMEvent( Data, NewData = False )
                            self.UpperWindow.move( Line, 0)
                            if self.UpperSelectedLine != None:
                                self.UpperSelectedLine += 1

            self.PrintMenu()

            self.UpperVisibleMaxIdx = (
                self.UpperVisibleMinIdx + ( self.UpperWindowMaxY - 1 ))
            
            self.LowerVisibleMaxIdx = (
                self.LowerVisibleMinIdx + ( self.LowerWindowMaxY - 1 ))

            LastUpperLineData = self.UpperWindow.instr(
                ( self.UpperWindowMaxY - 1 ), 0 ).decode('utf-8').strip() 

            self.UpperWindow.move( 
                self.UpperWindowMaxY - 1,
                len( LastUpperLineData ) - 1)
                
            LastLowerLineData = self.LowerWindow.instr(
                ( self.LowerWindowMaxY - 1 ), 0 ).decode('utf-8').strip()

            self.LowerWindow.move( 
                self.LowerWindowMaxY - 1,
                len( LastLowerLineData ) - 1)

            if (( self.UpperSelectedLine != None ) and
                ( self.UpperSelectedLine > ( self.UpperWindowMaxY - 1 ))):
                    self.UpperSelectedLine = None

            if (( self.LowerSelectedLine != None ) and
                ( self.LowerSelectedLine > ( self.LowerWindowMaxY - 1 ))):
                    self.LowerSelectedLine = None

            
        except BaseException as PossibleFailure:
            ...
            
    def ResizeLowerMode( self ):

        self.InitializeCurses()
        self.InitializeWindows()

        try:
            ( self.MainWindowMinY,
              self.MainWindowMinX, )  = self.MainWindow.getbegyx()
            ( self.MainWindowMaxY,
              self.MainWindowMaxX, )  = self.MainWindow.getmaxyx()

            self.LowerWindow.resize(  self.MainWindowMaxY - 1,
                                      self.MainWindowMaxX - 1 )

            self.LowerWindow.mvwin( 0, 0 )

            ( self.LowerWindowMinY,
              self.LowerWindowMinX, )  = self.LowerWindow.getbegyx()
            ( self.LowerWindowMaxY,
              self.LowerWindowMaxX, )  = self.LowerWindow.getmaxyx()
            ( self.UpperWindowMinY,
              self.UpperWindowMinX, )  = self.UpperWindow.getbegyx()
            ( self.UpperWindowMaxY,
              self.UpperWindowMaxX, )  = self.UpperWindow.getmaxyx()

            self.LowerWindow.bkgd( ' ', curses.color_pair(
                                        Screen.YELLOW_ON_MEDIUM_GREEN ))
            self.LowerWindow.refresh()
            self.SelectedWindow = Screen.LowerWindow
            
            for Line in range( 0, self.LowerWindowMaxY ):
                
                LineData = self.LowerWindow.instr(
                    ( Line ), 0 ).decode( 'utf-8' ).strip()
                                            
                if not LineData:
                    if self.LowerVisibleMaxIdx < ( len(self.LowerDataQueue) - 1 ):
                        self.LowerVisibleMaxIdx += 1
                        Data = self.LowerDataQueue[self.LowerVisibleMaxIdx]
                        self.LowerWindow.move( Line, 0)
                        self.PrintCDPEvent(Data, NewData = False)
                    else:
                        if self.LowerVisibleMinIdx > 0:
                            self.LowerWindow.move( 0, 0)
                            self.LowerWindow.insertln()
                            self.LowerVisibleMinIdx -= 1
                            Data = self.LowerDataQueue[self.LowerVisibleMinIdx]
                            self.PrintCDPEvent( Data, NewData = False )
                            self.LowerWindow.move( Line, 0)
                            if self.LowerSelectedLine != None:
                                self.LowerSelectedLine += 1
                    
            self.PrintMenu()

            self.UpperVisibleMaxIdx = (
                self.UpperVisibleMinIdx + ( self.UpperWindowMaxY - 1 ))
            
            self.LowerVisibleMaxIdx = (
                self.LowerVisibleMinIdx + ( self.LowerWindowMaxY - 1 ))

            LastUpperLineData = self.UpperWindow.instr(
                ( self.UpperWindowMaxY - 1 ), 0 ).decode('utf-8').strip() 

            self.UpperWindow.move( 
                self.UpperWindowMaxY - 1,
                len( LastUpperLineData ) - 1)
                
            LastLowerLineData = self.LowerWindow.instr(
                ( self.LowerWindowMaxY - 1 ), 0 ).decode('utf-8').strip()

            self.LowerWindow.move( 
                self.LowerWindowMaxY - 1,
                len( LastLowerLineData ) - 1)

            if (( self.UpperSelectedLine != None ) and
                ( self.UpperSelectedLine > ( self.UpperWindowMaxY - 1 ))):
                    self.UpperSelectedLine = None

            if (( self.LowerSelectedLine != None ) and
                ( self.LowerSelectedLine > ( self.LowerWindowMaxY - 1 ))):
                    self.LowerSelectedLine = None
                    
            
        except BaseException as PossibleFailure:
            ...

    def ResizeDetailMode( self ):

        self.InitializeCurses()
        self.InitializeWindows()

        try:
            ( self.MainWindowMinY,
              self.MainWindowMinX, )  = self.MainWindow.getbegyx()

            ( self.MainWindowMaxY,
              self.MainWindowMaxX, )  = self.MainWindow.getmaxyx()
              
            self.SelectedWindow = Screen.MainWindow
            self.Mode           = Screen.DetailMode
            self.MainWindow.move( 0, 0 )
            self.MainWindow.clear()
            self.Print( Screen.MainWindow, self.DetailDataEvent )
            
            self.PrintMenu()   

            LastLineData = self.MainWindow.instr(
                ( self.MainWindowMaxY - 1 ), 0 ).decode('utf-8').strip() 

            self.MainWindow.move( 
                self.MainWindowMaxY - 1,
                len( LastLineData ) - 1)

            
        except BaseException as PossibleFailure:
            ...

    def ResizeSplitMode( self ):

        try:
            self.InitializeCurses()
            self.InitializeWindows()

            ( self.MainWindowMinY,
              self.MainWindowMinX, )  = self.MainWindow.getbegyx()
            ( self.MainWindowMaxY,
              self.MainWindowMaxX, )  = self.MainWindow.getmaxyx()

            SizeAdjust = 0
            if self.MainWindowMaxY % 2 == 0: SizeAdjust = 1
            
            self.UpperWindow.resize( 
                ( self.MainWindowMaxY // 2 ) - SizeAdjust,
                  self.MainWindowMaxX  - 1  )

            ( self.UpperWindowMinY,
              self.UpperWindowMinX, )  = self.UpperWindow.getbegyx()

            ( self.UpperWindowMaxY,
              self.UpperWindowMaxX, )  = self.UpperWindow.getmaxyx()

            self.LowerWindow.resize( 
                self.MainWindowMaxY // 2,
                self.MainWindowMaxX  - 1 )

            self.LowerWindow.mvwin( self.UpperWindowMaxY, 0 )
            
            ( self.LowerWindowMinY,
              self.LowerWindowMinX, )  = self.LowerWindow.getbegyx()

            ( self.LowerWindowMaxY,
              self.LowerWindowMaxX, )  = self.LowerWindow.getmaxyx()

            self.UpperWindow.refresh()
            self.LowerWindow.refresh()

            LastUpperLineData = self.UpperWindow.instr(
                ( self.UpperWindowMaxY - 1 ), 0 )
                
            LastUpperLineData = (
                LastUpperLineData.decode( 'utf-8' ).strip() )
                            
            if not LastUpperLineData:
            
                if self.UpperVisibleMaxIdx < ( len(self.UpperDataQueue) - 1 ):
                    self.UpperVisibleMaxIdx += 1
                    Data = self.UpperDataQueue[self.UpperVisibleMaxIdx]
                    self.UpperWindow.move(self.UpperWindowMaxY - 1, 0)
                    self.PrintDOMEvent(Data, NewData = False)
                else:
                    if self.UpperVisibleMinIdx > 0:
                        self.UpperWindow.move( 0, 0)
                        self.UpperWindow.insertln()
                        self.UpperVisibleMinIdx -= 1
                        Data = self.UpperDataQueue[self.UpperVisibleMinIdx]
                        self.PrintDOMEvent( Data, NewData = False )
                        self.UpperWindow.move(self.UpperWindowMaxY - 1, 0)
                        if self.UpperSelectedLine != None:
                            self.UpperSelectedLine += 1
            
            LastLowerLineData = self.LowerWindow.instr(
                ( self.LowerWindowMaxY - 1 ), 0 )
                
            LastLowerLineData = (
                LastLowerLineData.decode('utf-8').strip() )
                            
            if not LastLowerLineData:
            
                if self.LowerVisibleMaxIdx < ( len(self.LowerDataQueue) - 1 ):
                    self.LowerVisibleMaxIdx += 1
                    Data = self.LowerDataQueue[self.LowerVisibleMaxIdx]
                    self.LowerWindow.move(self.LowerWindowMaxY - 1, 0)
                    self.PrintCDPEvent(Data, NewData = False)
                else:
                    if self.LowerVisibleMinIdx > 0:
                        self.LowerWindow.move( 0, 0)
                        self.LowerWindow.insertln()
                        self.LowerVisibleMinIdx -= 1
                        Data = self.LowerDataQueue[self.LowerVisibleMinIdx]
                        self.PrintCDPEvent( Data, NewData = False )
                        self.LowerWindow.move(self.LowerWindowMaxY - 1, 0)
                        if self.LowerSelectedLine != None:
                            self.LowerSelectedLine += 1


            self.PrintMenu()
            
            self.UpperVisibleMaxIdx = (
                self.UpperVisibleMinIdx + ( self.UpperWindowMaxY - 1 ))
            
            self.LowerVisibleMaxIdx = (
                self.LowerVisibleMinIdx + ( self.LowerWindowMaxY - 1 ))

            LastUpperLineData = self.UpperWindow.instr(
                ( self.UpperWindowMaxY - 1 ), 0 ).decode('utf-8').strip() 

            self.UpperWindow.move( 
                self.UpperWindowMaxY - 1,
                len( LastUpperLineData ) - 1)
                
            LastLowerLineData = self.LowerWindow.instr(
                ( self.LowerWindowMaxY - 1 ), 0 ).decode('utf-8').strip()

            self.LowerWindow.move( 
                self.LowerWindowMaxY - 1,
                len( LastLowerLineData ) - 1)

            if (( self.UpperSelectedLine != None ) and
                ( self.UpperSelectedLine > ( self.UpperWindowMaxY - 1 ))):
                    self.UpperSelectedLine = None

            if (( self.LowerSelectedLine != None ) and
                ( self.LowerSelectedLine > ( self.LowerWindowMaxY - 1 ))):
                    self.LowerSelectedLine = None
            
        except BaseException as PossibleFailure:
            ...

    def InitializeColors( self ):

        Screen.YELLOW           = 100
        Screen.BLUE             = 101
        Screen.WHITE            = 102
        Screen.BLACK            = 103
        Screen.GREEN            = 104
        Screen.RED              = 105
        Screen.PURPLE           = 106

        Screen.MEDIUM_GREEN     = 150
        Screen.MEDIUM_BLUE      = 151
        Screen.MEDIUM_RED       = 152

        curses.init_color(  Screen.BLACK,        *(     0,     0,     0   ,))
        curses.init_color(  Screen.YELLOW,       *(  1000,  1000,     0   ,))
        curses.init_color(  Screen.BLUE,         *(     0,    0,   1000   ,))
        curses.init_color(  Screen.WHITE,        *(  1000,  1000,  1000   ,))
        curses.init_color(  Screen.GREEN,        *(     0,  1000,     0   ,))
        curses.init_color(  Screen.RED,          *(  1000,     0,     0   ,))
        curses.init_color(  Screen.PURPLE,       *(   352,     8,  692   ,))

        curses.init_color(  Screen.MEDIUM_RED,   *(   500,     0,     0   ,))
        curses.init_color(  Screen.MEDIUM_GREEN, *(     0,   450,     0   ,))
        curses.init_color(  Screen.MEDIUM_BLUE,  *(     0,     0,   750   ,))

        Screen.YELLOW_ON_BLUE           = 200
        Screen.WHITE_ON_BLUE            = 201
        Screen.YELLOW_ON_MEDIUM_GREEN   = 202
        Screen.YELLOW_ON_MEDIUM_BLUE    = 203
        Screen.YELLOW_ON_MEDIUM_RED     = 204
        Screen.WHITE_ON_MEDIUM_BLUE     = 205
        Screen.WHITE_ON_MEDIUM_GREEN    = 206
        Screen.WHITE_ON_MEDIUM_RED      = 207
        Screen.WHITE_ON_BLACK           = 208
        Screen.WHITE_ON_PURPLE          = 209
        Screen.RED_ON_BLACK             = 210

        curses.init_pair(   Screen.YELLOW_ON_BLUE,
                            Screen.YELLOW, Screen.BLUE )
        curses.init_pair(   Screen.WHITE_ON_BLUE,
                            Screen.WHITE, Screen.BLUE )
        curses.init_pair(   Screen.YELLOW_ON_MEDIUM_GREEN,
                            Screen.YELLOW, Screen.MEDIUM_GREEN )
        curses.init_pair(   Screen.YELLOW_ON_MEDIUM_BLUE,
                            Screen.YELLOW, Screen.MEDIUM_BLUE )
        curses.init_pair(   Screen.YELLOW_ON_MEDIUM_RED,
                            Screen.YELLOW, Screen.MEDIUM_RED )
        curses.init_pair(   Screen.WHITE_ON_MEDIUM_BLUE,
                            Screen.WHITE, Screen.MEDIUM_BLUE )
        curses.init_pair(   Screen.WHITE_ON_MEDIUM_GREEN,
                            Screen.WHITE, Screen.MEDIUM_GREEN )
        curses.init_pair(   Screen.WHITE_ON_MEDIUM_RED,
                            Screen.WHITE, Screen.MEDIUM_RED )
        curses.init_pair(   Screen.WHITE_ON_BLACK,
                            Screen.WHITE, Screen.BLACK )
        curses.init_pair(   Screen.RED_ON_BLACK,
                            Screen.RED, Screen.BLACK )
        curses.init_pair(   Screen.WHITE_ON_PURPLE,
                            Screen.WHITE, Screen.PURPLE )



    def PrintCDPEvent( self, CDPEvent, Selected = False, NewData = True ):

        CurrentY, CurrentX  = self.LowerWindow.getyx()    
        RemainingLength     = self.LowerWindowMaxX - 1

        if NewData:
            if  (( CurrentY > 0 )  or
                (( CurrentY == 0)  and  ( CurrentX > 0 ))):
                    self.LowerWindow.addch( '\n' )
                    RemainingLength -= 1
        else:
            self.LowerWindow.clrtoeol()

        EventTypeColorPair = curses.color_pair(
                             Screen.YELLOW_ON_MEDIUM_GREEN )
        OutputStrColorPair = curses.color_pair(
                             Screen.WHITE_ON_MEDIUM_GREEN )

        if Selected:
            EventTypeColorPair = curses.color_pair(
                                 Screen.YELLOW_ON_MEDIUM_RED )
            OutputStrColorPair = curses.color_pair(
                                 Screen.WHITE_ON_MEDIUM_RED )

        self.LowerWindow.addstr( CDPEvent.Method + ': ',
                                 EventTypeColorPair )
        
        RemainingLength = ( RemainingLength - 
                          ( len( CDPEvent.Method ) + 2 ))

        OutputStr = ''
        
        if CDPEvent.Params:
            OutputStr = json.dumps(CDPEvent.Params)
        else:
            OutputStr = "No Additional Information"
                
        if len(OutputStr) > RemainingLength:
            OutputStr = OutputStr[:RemainingLength]

        self.LowerWindow.addstr( OutputStr,
                                 OutputStrColorPair )
                                 
        self.LowerWindow.refresh()

        if NewData:
            CurrentY, CurrentX = self.LowerWindow.getyx()
            if CurrentY < ( self.LowerWindowMaxY - 1):
                self.LowerVisibleMaxIdx = len(self.LowerDataQueue) - 1
                self.LowerVisibleMinIdx = 0
            else:
                self.LowerVisibleMaxIdx = len(self.LowerDataQueue) - 1
                self.LowerVisibleMinIdx = self.LowerVisibleMaxIdx - (self.LowerWindowMaxY - 1)
            if self.LowerSelectedLine != None:
                if CurrentY == self.LowerWindowMaxY - 1:
                    self.LowerSelectedLine -= 1
                    if self.LowerSelectedLine < 0:
                        self.LowerSelectedLine = None

        

    def PrintDOMEvent( self, DOMEvent, Selected = False, NewData = True ):

        CurrentY, CurrentX  = self.UpperWindow.getyx()    
        RemainingLength     = self.UpperWindowMaxX - 1
        
        if NewData:
            if  (( CurrentY > 0 )  or
                (( CurrentY == 0)  and  ( CurrentX > 0 ))):
                    self.UpperWindow.addch( '\n' )
                    RemainingLength -= 1
        else:
            self.UpperWindow.clrtoeol()

        EventTypeColorPair = curses.color_pair(
                             Screen.YELLOW_ON_MEDIUM_BLUE )
        OutputStrColorPair = curses.color_pair(
                             Screen.WHITE_ON_MEDIUM_BLUE )

        if Selected:
            EventTypeColorPair = curses.color_pair(
                                 Screen.YELLOW_ON_MEDIUM_RED )
            OutputStrColorPair = curses.color_pair(
                                 Screen.WHITE_ON_MEDIUM_RED )

        self.UpperWindow.addstr( DOMEvent.DOMEventType + ': ',
                                 EventTypeColorPair )
        
        RemainingLength = ( RemainingLength - 
                          ( len( DOMEvent.DOMEventType ) + 2 ))
        
        EventItems      = [ 'TargetProto', 'TargetName', 'TargetTagName', 
                            'TargetClassName', 'EventMessage', 'EventError', 
                            'TargetText' ]

        OutputStr = ''
        
        for Idx, EventItem in enumerate(EventItems):
            ItemValue = getattr( DOMEvent, EventItem )
            if ItemValue:
                if Idx > 0: OutputStr += ' | '
                OutputStr += ItemValue
        
        if len(OutputStr) > RemainingLength:
            OutputStr = OutputStr[:RemainingLength]

        self.UpperWindow.addstr( OutputStr,
                                 OutputStrColorPair )

        if NewData:
            CurrentY, CurrentX = self.UpperWindow.getyx()
            if CurrentY < ( self.UpperWindowMaxY - 1):
                self.UpperVisibleMaxIdx = len(self.UpperDataQueue) - 1
                self.UpperVisibleMinIdx = 0
            else:
                self.UpperVisibleMaxIdx = len(self.UpperDataQueue) - 1
                self.UpperVisibleMinIdx = self.UpperVisibleMaxIdx - (self.UpperWindowMaxY - 1)
            if self.UpperSelectedLine != None:
                if CurrentY == self.UpperWindowMaxY - 1:
                    self.UpperSelectedLine -= 1
                    if self.UpperSelectedLine < 0:
                        self.UpperSelectedLine = None
                                
        self.UpperWindow.refresh()

    def PrintEventDetail( self, EventData, 
                          DetailMinIdx = None, 
                          DetailMaxIdx = None,
                          DOMDetailType = None ):
    
        CurrentY, CurrentX  = self.MainWindow.getyx()    

        if hasattr( EventData, 'DOMEventType' ):

            if not DOMDetailType:  
                DOMDetailType = Screen.DOMEventDetail
                
            if DOMDetailType == Screen.DOMEventDetail:
                self.DetailDataOutput = (
                    json.dumps( 
                    EventData.DOMEventDetail.Response, 
                    indent = 2 ).split( '\n' ))
                    
            if DOMDetailType == Screen.DOMEventTargetDetail:
                self.DetailDataOutput = (
                    json.dumps( 
                    EventData.DOMEventTargetDetail.Response, 
                    indent = 2 ).split( '\n' ))
        else:
        
            EventData.GetCDPEventDetails( self.ExecuteMethod, self.SendCommand )
            
            self.DetailDataOutput = (
                json.dumps( 
                EventData.Message, indent = 2 ).split( '\n' ))
            
        if DetailMinIdx == None:
            self.DetailVisibleMinIdx = self.MainWindowMinY
        else:
            self.DetailVisibleMinIdx = DetailMinIdx

        if DetailMaxIdx == None:
            if len(self.DetailDataOutput) < (self.MainWindowMaxY):
                self.DetailVisibleMaxIdx = len(self.DetailDataOutput) 
            else:
                self.DetailVisibleMaxIdx = self.DetailVisibleMinIdx + (self.MainWindowMaxY - 1)
        else:
            self.DetailVisibleMaxIdx = DetailMaxIdx
        
        self.MainWindow.move( 0, 0 )
        self.MainWindow.clear()
        
        for Idx in range( self.DetailVisibleMinIdx, 
                          self.DetailVisibleMaxIdx ):
            
            Line = self.DetailDataOutput[ Idx ]

            if ( len( Line ) + 1 ) > ( self.MainWindowMaxX - 1 ):
                Line = Line[:( self.MainWindowMaxX - 1 )]
            
            self.MainWindow.addstr( 
                Line,
                curses.color_pair( Screen.WHITE_ON_BLACK ))
            
            if Idx < self.DetailVisibleMaxIdx:
                self.MainWindow.addch( '\n' )
                    
        self.MainWindow.refresh()
        self.PrintMenu()

    
    def Print( self, WindowID, EventData ):
        
        try:
            match WindowID:
            
                case Screen.MainWindow:
                    self.PrintEventDetail( EventData )

                case Screen.UpperWindow:
                    self.PrintDOMEvent( EventData )

                case Screen.LowerWindow:
                    self.PrintCDPEvent( EventData )

                case _:
                    print('Unknown Window ID')
                    return False

        except BaseException as Failure:
            print( GetExceptionInfo( Failure ))
            os._exit(1)

    ...


if __name__ == '__main__':
    print("Hello World")



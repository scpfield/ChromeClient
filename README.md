
ChromeClient

Still under construction, not yet complete and needs optimizations.

Basic summary:

1.  Client connects to Chrome browser on the debug port and uses the [DevTools Protocol](https://chromedevtools.github.io/devtools-protocol/) to register as a listener for CDP Events and DOM Events.

2.  Client uses text-mode curses library to display results in real-time.  This was my first time working with curses.

...

The two main dependencies is the [Python CDP](https://py-cdp.readthedocs.io/en/latest/) package which provides object wrappers for the JSON CDP wire messages, and also [Python websocket-client](https://websocket-client.readthedocs.io/en/latest/) for transport.

...

To register as a listener for DOM Events, such as mouse-clicks, keyboard activity, messages, errors, any type of DOM event, I used a CDP protocol method to inject a Javascript function which calls addEventListener() for every DOM Event that exists in "Window".  I simply wrote the Javascript function as a Python string.  When DOM Events occur and the Javascript listener is called, it dumps the Event + Target information to console.log, which the CDP protocol sends to the Client.  Information about the [CDP injection method](https://chromedevtools.github.io/devtools-protocol/tot/Page/#method-addScriptToEvaluateOnNewDocument).

The CDP Events are not traditional DOM Events, they are the Chrome-specific debugging events. Each of the CDP Domains have various Events that can potentially be created and delivered to a CDP Client.  There are very interesting ones, in particular you can be notified for changes to the DOM tree in real-time, as nodes are added / removed / changed, although sometimes it is a challenge to get it working properly.

Here are a few screenshots.  The default mode is Split-Screen view.  Both windows continuously scroll as new data arrives from Chrome.  The upper window is for the DOM Events, the lower window is for the CDP Events.



![image](https://github.com/scpfield/ChromeClient/assets/95513302/c5af4c05-1014-4329-96f0-3094980ed6c6)


There can be quite a lot of Events happening, so there is Pause + Resume capability.  Items in each window are selectable by clicking on them with a mouse.  Once selected, the Arrow Keys work for scrolling up and down through the buffers of saved events in memory.  Currently there is no max buffer size.  You can also switch into Full-Screen mode for either DOM or CDP Events if the Split Screen is becoming annoying.  

If an Item is selected, the user can hit Enter or double-click, which will display the Detail view of the selected Event, because there is way too much information about an Event to display in a single line.  The Detail view dumps the raw JSON message from Chrome.





### ChromeClient

Still under construction, not yet complete and needs optimizations.

Basic summary:

1.  Client connects to Chrome browser on the debug port and uses the [DevTools Protocol](https://chromedevtools.github.io/devtools-protocol/) to register as a listener for CDP Events and DOM Events.

2.  Client uses text-mode curses library to display results in real-time.  This was my first time working with curses.

...

The two main dependencies are the [Python CDP](https://py-cdp.readthedocs.io/en/latest/) package which provides object wrappers for the JSON CDP wire messages, and also [Python websocket-client](https://websocket-client.readthedocs.io/en/latest/) for transport.

To register as a listener for DOM Events, such as mouse-clicks, keyboard activity, messages, errors, any type of DOM event, I used a CDP protocol method to inject a Javascript function which calls addEventListener() for every DOM Event that exists in "Window".  I simply wrote the Javascript function as a Python string.  When DOM Events occur and the Javascript listener is called, it dumps the Event + Target information to console.log, which the CDP protocol sends to the Client.  The Client obtains the internal object IDs and queries further data about the Events.  Information about the [CDP injection method](https://chromedevtools.github.io/devtools-protocol/tot/Page/#method-addScriptToEvaluateOnNewDocument).

The CDP Events are not traditional DOM Events, they are the Chrome-specific debugging events. Each of the CDP Domains have various Events that can potentially occur and delivered to a CDP Client.  There are very interesting ones, in particular you can be notified for changes to the DOM tree in real-time, as nodes are added / removed / changed, although sometimes it is a challenge to get it working properly.

Here are a few screenshots.  The default mode is Split-Screen view.  Both windows continuously scroll as new data arrives from Chrome.  The upper window is for the DOM Events, the lower window is for the CDP Events.


![image](https://github.com/scpfield/ChromeClient/assets/95513302/c5af4c05-1014-4329-96f0-3094980ed6c6)


The overall console window is resizable.  Though, the Windows curses support is a bit flakey, and my code for dynamically resizing the split-screen and keeping everything in sync might have a bug or two, but mostly it works.

There can be quite a lot of Events happening very fast, so there is Pause + Resume capability.  Items in each window are selectable by clicking on them with a mouse.  Once selected, the Arrow Keys work for scrolling up and down through the buffers of saved events in memory.  Currently there is no max buffer size.  You can also switch into Full-Screen mode for either DOM or CDP Events if the Split Screen is becoming annoying.  


![image](https://github.com/scpfield/ChromeClient/assets/95513302/e3b17253-4ca4-4536-8390-7e9c5282d809)


If an Item is selected, the user can hit Enter or double-click, which displays the Detail view of the selected Event, because there is way too much information about an Event to display in a single line.  The Detail view dumps the raw JSON message from Chrome.

One thing I learned with Curses, it is similar to all other UI frameworks in that you cannot have multiple threads concurrently accessing UI elements.  At first I tried protecting each UI element with locks and such but it was error-prone and not very reliable.  So instead I run the all the curses UI code in a single, separate Python thread that reads from input queues for anything that needs to touch the UI.  Client modules that need to add / update the UI post messages to the input queues which the single UI thread reads from.  

For DOM events, the user can either view the Event detail or the Target detail  (the target of the event).  This is what the Event detail view looks like.  Pretty basic.  It is scrollable by using the Arrow keys.

Detail view for a Key event.

![image](https://github.com/scpfield/ChromeClient/assets/95513302/a7babac6-d7b8-4956-9b8d-9828ee7508d8)


Target view of the Key event.

![image](https://github.com/scpfield/ChromeClient/assets/95513302/0b741c28-935c-470a-8c02-6d7efcb803e0)


I want to add a Copy To Clipboard option but it would require additional dependencies and potential cross-platform issues.

For CDP Events, this is an example of a "childNodeInserted" Event.  Most/all of the CDP Events refer to internal NodeIds, which you can use in various CDP functions to query further information, but it doesn't always work,  the NodeIds seem to be ephemeral.  NodeIds also map to Javascript RemoteObjectIds which are more reliable.


![image](https://github.com/scpfield/ChromeClient/assets/95513302/adc541d4-1a15-42f7-9a53-afcddb6da3f1)


I plan to retrieve all the further Node information for the CDP Detail views, instead of showing just the NodeIds.  

...

Here is an example of an "animationStarted" CDP Event, for my favorite testing app, the Nessus app when it displays the Spinning Icon.


![image](https://github.com/scpfield/ChromeClient/assets/95513302/af92dc0d-a1a7-4b69-8e92-97b70112c488)


It also has a few Javascript Parse Failures too, but so does Microsoft and other popular web sites, so who knows.


![image](https://github.com/scpfield/ChromeClient/assets/95513302/f764d879-c0f9-4a4a-94cb-acf5ff28b9be)


Finally, here are two short videos of what it looks like when running.

[The first video](https://www.loom.com/share/9d258db5fb82405b8524c0e2fe63237d) is using my favorite Tenable test app, and you will notice that due to the large volume of Mouse Events (not a bug in Tenable),  my code takes a little while to catch-up.  I should probably exclude some of these mouse events because there are so many that are triggered, they tend to drown out the other ones.

[The second video](https://www.loom.com/share/63dbb7f4e709407b9f12f4fd1f9c7266) is microsoft.com's home page.  It is funny.  All it does is generate "transition" related events as it automatically scrolls through various slides.  I didn't click or navigate the site at all, but just monitoring what it does.  Each time it transitions to a new slide, a short burst of both DOM and CDP events occur.



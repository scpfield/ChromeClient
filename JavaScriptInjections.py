import sys, os

AddPageLoadListeners = (

    "   window.addEventListener( 'load', (evt) =>                       " +
    "   {                                                               " +
    "       console.log( evt );                                         " +
    "   },  false );                                                    " +
    "                                                                   " +
    "   document.addEventListener( 'readystatechange', (evt) =>         " +
    "   {                                                               " +
    "       console.log( evt );                                         " +
    "   },  false );                                                    " +
    "                                                                   " +
    "   document.addEventListener( 'DOMContentLoaded', (evt) =>         " +
    "   {                                                               " +
    "       console.log( evt );                                         " +
    "   },  false );                                                    " +
    "                                                                   " +
    "   document.addEventListener( 'click', (evt) =>                    " +
    "   {                                                               " +
    "       console.log( evt );                                         " +
    "   },  false );                                                    " +
    "                                                                   " )

AddAllEventsListener = (
    "                                                                       " +
    "   function addAllEventsListener( target, listener, ...Args )          " +
    "   {                                                                   " +
    "        for (const key in target)                                      " +
    "        {                                                              " +
    "            if (/^on/.test(key))                                       " +
    "            {                                                          " +
    "                const eventType = key.substr(2);                       " +
    "                target.addEventListener(                               " +
    "                    eventType, listener, ...Args);                     " +
    "            }                                                          " +
    "        }                                                              " +
    "                                                                       " +
    "    }                                                                  " +
    "                                                                       " +
    "    addAllEventsListener( window, (evt) =>                             " +
    "    {                                                                  " +
    "        console.log(   'EventObjects',                                 " +
    "                       evt,                                            " +
    "                       evt.target,                                     " +
    "                       {'DOMEventType' : evt.type},                    " +
    "                       {'TargetName' : Object(evt.target)},            " +
    "                       {'TargetProto' : evt.target.__proto__},         " +
    "                       {'TargetTagName' : evt.target.tagName},         " +
    "                       {'TargetText' : evt.target.textContent},        " +
    "                       {'EventError' : JSON.stringify(evt.error)},     " +
    "                       {'EventMessage' : JSON.stringify(evt.data)},    " +
    "                       {'TargetClassName' : evt.target.className} );   " +
    "    }, false );                                                        " +
    "                                                                       " )




# Object.keys(my_object)
# console.log(JSON.parse(JSON.stringify(Event)));            
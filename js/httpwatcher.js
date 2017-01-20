/**
 * Live reload script for httpwatcher: https://github.com/thanethomson/httpwatcher
 */

var ReconnectingWebSocket = require('reconnectingwebsocket');
var connection = null;
var storageSet = function() {};
var storageGet = function() { return null; };
var storageHas = function() { return false; };
var storageClear = function() {};

if (typeof(Storage) !== "undefined") {
    storageSet = function(k, v) {
        window.localStorage.setItem(k, v);
    };
    storageGet = function(k) {
        return window.localStorage.getItem(k);
    };
    storageHas = function(k) {
        return storageGet(k) !== null;
    };
    storageClear = function(k) {
        window.localStorage.removeItem(k);
    }
}

function getWindowScrollPosition() {
    var top = 0, left = 0;

    if (typeof(window.pageYOffset) == 'number') {
        top = window.pageYOffset;
        left = window.pageXOffset;
    } else if (document.body && (document.body.scrollLeft || document.body.scrollTop)) {
        top = document.body.scrollTop;
        left = document.body.scrollLeft;
    } else if (document.documentElement && (document.documentElement.scrollLeft || document.documentElement.scrollTop)) {
        top = document.documentElement.scrollTop;
        left = document.documentElement.scrollLeft;
    }

    return {
        x: left,
        y: top
    };
}

function restoreWindowScrollPosition() {
    // if we're still at the same location
    if (window.location.href == storageGet('scroll-for')) {
        var x = storageGet('scroll-x'), y = storageGet('scroll-y');
        window.scrollTo(x, y);
    }

    // always clear the stored scroll position info, in case the user clicks on a link
    // that takes them to the same page (where scroll position shouldn't be saved)
    storageClear('scroll-for');
    storageClear('scroll-x');
    storageClear('scroll-y');
}

function saveWindowScrollPosition() {
    var coords = getWindowScrollPosition();
    storageSet('scroll-for', window.location.href);
    storageSet('scroll-x', coords.x);
    storageSet('scroll-y', coords.y);
}

function httpwatcher(webSocketUrl) {
    if (connection == null) {
        connection = new ReconnectingWebSocket(webSocketUrl);
        connection.onerror = function(e) {
            console.log("WebSocket error: "+e);
        };
        connection.onmessage = function(m) {
            msg = JSON.parse(m.data);
            if (msg.command && msg.command == "reload") {
                // first we save our scroll position
                saveWindowScrollPosition();
                // then we do a hard reload
                window.location.reload(true);
            }
        };

        // try to restore the scroll position
        restoreWindowScrollPosition();
    }
}

// Global export of the httpwatcher() function
window.httpwatcher = httpwatcher;

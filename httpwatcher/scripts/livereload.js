/**
 * Live reload script for httpwatcher: https://github.com/thanethomson/httpwatcher
 */

var connection = null;

function livereload(webSocketUrl) {
    if (connection == null) {
        connection = new WebSocket(webSocketUrl);
        connection.onerror = function(e) {
            console.log("WebSocket error: "+e);
        };
        connection.onmessage = function(m) {
            msg = JSON.parse(m.data);
            if (msg.command && msg.command == "reload") {
                window.location.reload(true);
            }
        };
    }
}

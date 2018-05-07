(function() {
function ready(fn) {
  if (document.attachEvent ? document.readyState === "complete" : document.readyState !== "loading"){
    fn();
  } else {
    document.addEventListener('DOMContentLoaded', fn);
  }
}

var lastSavedTime = 0;
var saveFrequency = 10; // in milliseconds

function init() {
	var player = document.getElementById('player');
	// Does not work: must be trigered by button
	/*
	if (player.requestFullscreen) {
		player.requestFullscreen();
	}*/
	// Need to be specialized per file (or at least delete if not the same
	player.ontimeupdate = function() {
		newTime = player.currentTime;
		if (Math.abs(newTime - lastSavedTime) > saveFrequency) {
			console.log('saving position ' + newTime);
			lastSavedTime = newTime;
			localStorage.setItem('currentTime', newTime);
		}
	};

	var prevTime = localStorage.getItem('currentTime');
	if (prevTime) {
		player.currentTime = prevTime;
		lastSavedTime = prevTime;
	}
}

ready(init);

}());

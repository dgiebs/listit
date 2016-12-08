// modified from https://fullcalendar.io/docs/

// Get today's date in Javascript
// http://stackoverflow.com/questions/1531093/how-to-get-current-date-in-javascript
var today = new Date();
var dd = today.getDate();
var mm = today.getMonth()+1; //January is 0!
var yyyy = today.getFullYear();

if(dd<10) {
    dd='0'+dd
} 

if(mm<10) {
    mm='0'+mm
} 
today = yyyy + '-' + mm +'-'+dd;
	
$(document).ready(function() {
	$('#calendar').fullCalendar({
		header: {
			left: 'prev,next today',
			center: 'title',
			right: 'month,agendaWeek,agendaDay,listWeek'
		},
		defaultDate: today,
		navLinks: true, // can click day/week names to navigate views
		editable: true,
		eventLimit: true, // allow "more" link when too many events
		events: Flask.url_for("events")
	});
});
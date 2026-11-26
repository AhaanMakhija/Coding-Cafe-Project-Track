// ORBIT calendar: draws FullCalendar and wires up the layer toggles.
// The data comes from two JSON routes, whose URLs are read from data-* attributes
// on #calendar so this file never hard-codes a URL.

document.addEventListener("DOMContentLoaded", () => {
  const el = document.getElementById("calendar");
  if (!el || !window.FullCalendar) return;

  // One event source per layer. FullCalendar calls each URL with ?start=&end=
  // for the dates on screen and draws whatever JSON comes back.
  const sources = {
    campus:  { id: "campus",  url: el.dataset.eventsUrl,       color: "#1f5a63", textColor: "#fbf8f2" },
    course:  { id: "course",  url: el.dataset.courseEventsUrl, color: "#6b4f9e", textColor: "#fbf8f2" },
    classes: { id: "classes", url: el.dataset.classesUrl,      color: "#e2552d", textColor: "#fbf8f2" },
  };

  const calendar = new FullCalendar.Calendar(el, {
    initialView: window.innerWidth < 760 ? "listWeek" : "timeGridWeek",
    firstDay: 1,                 // weeks start on Monday
    nowIndicator: true,
    height: "auto",
    slotMinTime: "07:00:00",
    slotMaxTime: "24:00:00",     // late deadlines (e.g. 11 PM) must still show
    allDaySlot: false,
    // 12-hour times with AM/PM everywhere, matching the rest of ORBIT ("2:30 PM").
    // meridiem must be set, or FullCalendar shortens "2:30 PM" to "2:30p" or drops it.
    eventTimeFormat: { hour: "numeric", minute: "2-digit", meridiem: "short", hour12: true },
    slotLabelFormat: { hour: "numeric", minute: "2-digit", meridiem: "short", hour12: true },
    headerToolbar: {
      left: "prev,next today",
      center: "title",
      right: "dayGridMonth,timeGridWeek,listWeek",
    },
    buttonText: { today: "Today", month: "Month", week: "Week", list: "List" },
    eventSources: Object.values(sources),
  });
  calendar.render();

  // Layer toggles: add or remove that layer's event source.
  document.querySelectorAll("input[data-layer]").forEach((box) => {
    box.addEventListener("change", () => {
      const layer = box.dataset.layer;
      const current = calendar.getEventSourceById(layer);
      if (box.checked && !current) calendar.addEventSource(sources[layer]);
      if (!box.checked && current) current.remove();
    });
  });
});

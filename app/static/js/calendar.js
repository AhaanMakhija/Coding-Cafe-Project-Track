// ORBIT calendar: draws FullCalendar and wires up the layer toggles.
// The data comes from two JSON routes, whose URLs are read from data-* attributes
// on #calendar so this file never hard-codes a URL.

document.addEventListener("DOMContentLoaded", () => {
  const el = document.getElementById("calendar");
  if (!el || !window.FullCalendar) return;

  // One event source per layer. FullCalendar calls each URL with ?start=&end=
  // for the dates on screen and draws whatever JSON comes back.
  const sources = {
    campus:  { id: "campus",  url: el.dataset.eventsUrl,  color: "#1f5a63", textColor: "#fbf8f2" },
    classes: { id: "classes", url: el.dataset.classesUrl, color: "#e2552d", textColor: "#fbf8f2" },
  };

  const calendar = new FullCalendar.Calendar(el, {
    initialView: window.innerWidth < 760 ? "listWeek" : "timeGridWeek",
    firstDay: 1,                 // weeks start on Monday
    nowIndicator: true,
    height: "auto",
    slotMinTime: "07:00:00",
    slotMaxTime: "22:00:00",
    allDaySlot: false,
    // 24-hour times everywhere, matching the rest of ORBIT ("14:00", not "2:00").
    eventTimeFormat: { hour: "2-digit", minute: "2-digit", hour12: false },
    slotLabelFormat: { hour: "2-digit", minute: "2-digit", hour12: false },
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

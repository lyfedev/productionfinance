// compare.js — the MapLibre layer for /compare (Phase 6, UI-02).
//
// Loaded as `<script type="module">`. Reads the server-rendered GeoJSON
// block and builds a data-driven marker layer on top of it. Guards on
// `#map` being present and on the MapLibre import succeeding — a failed
// CDN load or a missing container leaves the server-rendered page fully
// usable; no figure on this page exists only inside this script.
//
// Vocabulary discipline: this file is covered by the D-70 gate over
// app/static/ — every string and comment here stays clear of the
// product's prescriptive-vocabulary list (see 04-CONTEXT.md § D-70).

const MAP_CONTAINER_ID = "map";
const GEOJSON_SCRIPT_ID = "compare-geojson";
// The default falls back to the same OpenFreeMap style URL the server
// also renders as the map container's own `data-style-url` attribute
// (compare.html) — read from the DOM first so the server-declared config
// is the single source of truth; this constant only covers the
// no-container-yet code path, which never reaches buildMap() at all.
const DEFAULT_STYLE_URL = "https://tiles.openfreemap.org/styles/liberty";
const MAPLIBRE_MODULE_URL =
  "https://cdn.jsdelivr.net/npm/maplibre-gl@6.5.0/dist/maplibre-gl.mjs";

const RANKED_LAYER_ID = "compare-cities-ranked";
const UNRANKED_LAYER_ID = "compare-cities-unranked";

// UI-03: the start-date slider's own element ids and the settle delay
// (dragging fires many "input" events; the JSON re-ranking request only
// fires once dragging pauses).
const SLIDER_INPUT_ID = "pf-start-index";
const SLIDER_LABEL_ID = "pf-start-index-label";
const SLIDER_OPTIONS_ID = "pf-slider-options";
const SLIDER_FORM_ID = "pf-slider-form";
const RANKED_LIST_CONTAINER_ID = "pf-ranked-list-container";
const SLIDER_SETTLE_DELAY_MS = 350;

// Kept module-scoped (never returned to a caller, never read from a
// closure captured before the map exists) so a later settled slider
// position can update the SAME map instance's data source rather than
// tearing it down and rebuilding it.
let mapInstance = null;

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text == null ? "" : String(text);
  return div.innerHTML;
}

function readGeoJson() {
  const script = document.getElementById(GEOJSON_SCRIPT_ID);
  if (!script) {
    return null;
  }
  try {
    return JSON.parse(script.textContent);
  } catch (error) {
    console.error("compare.js: could not parse the embedded GeoJSON block", error);
    return null;
  }
}

function readSliderOptions() {
  const script = document.getElementById(SLIDER_OPTIONS_ID);
  if (!script) {
    return [];
  }
  try {
    return JSON.parse(script.textContent);
  } catch (error) {
    console.error("compare.js: could not parse the embedded slider-options block", error);
    return [];
  }
}

function rankedColorExpression(featureCollection) {
  const netRankedValues = featureCollection.features
    .filter((feature) => feature.properties.band === "net_ranked")
    .map((feature) => feature.properties.total_value);
  const minValue = netRankedValues.length ? Math.min(...netRankedValues) : 0;
  const maxValue = netRankedValues.length ? Math.max(...netRankedValues) : 1;
  // interpolate() requires a strictly increasing stop sequence — a single
  // ranked city (min === max) would otherwise raise at style-load time.
  const highStop = maxValue > minValue ? maxValue : minValue + 1;
  return ["interpolate", ["linear"], ["get", "total_value"], minValue, "#2a6f97", highStop, "#a4133c"];
}

// UI-03: re-point the already-built map at a fresh, server-priced
// GeoJSON FeatureCollection for a newly settled slider position — the
// colour ramp's own min/max are recomputed from THIS response's own
// figures, never carried over stale from the page's first load.
function updateMapData(featureCollection) {
  if (!mapInstance) {
    return;
  }
  const source = mapInstance.getSource("compare-cities");
  if (!source) {
    return;
  }
  source.setData(featureCollection);
  if (mapInstance.getLayer(RANKED_LAYER_ID)) {
    mapInstance.setPaintProperty(RANKED_LAYER_ID, "circle-color", rankedColorExpression(featureCollection));
  }
}

function buildMap(maplibregl, featureCollection) {
  const container = document.getElementById(MAP_CONTAINER_ID);
  const styleUrl = (container && container.dataset.styleUrl) || DEFAULT_STYLE_URL;

  const map = new maplibregl.Map({
    container: MAP_CONTAINER_ID,
    style: styleUrl,
    center: [-40, 40],
    zoom: 1.4,
  });
  mapInstance = map;

  map.addControl(new maplibregl.NavigationControl(), "top-right");

  map.on("load", () => {
    map.addSource("compare-cities", {
      type: "geojson",
      data: featureCollection,
    });

    map.addLayer({
      id: RANKED_LAYER_ID,
      type: "circle",
      source: "compare-cities",
      filter: ["==", ["get", "band"], "net_ranked"],
      paint: {
        "circle-radius": 15,
        "circle-color": rankedColorExpression(featureCollection),
        "circle-stroke-width": 2,
        "circle-stroke-color": "#ffffff",
      },
    });

    map.addLayer({
      id: UNRANKED_LAYER_ID,
      type: "circle",
      source: "compare-cities",
      filter: ["==", ["get", "band"], "incentive_not_modelled"],
      paint: {
        "circle-radius": 11,
        "circle-color": "#9a9488",
        "circle-stroke-width": 2,
        "circle-stroke-color": "#ffffff",
      },
    });

    const popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false });
    const bandLabel = {
      net_ranked: "ranked on net landed cost",
      incentive_not_modelled: "no incentive modelled",
    };

    for (const layerId of [RANKED_LAYER_ID, UNRANKED_LAYER_ID]) {
      map.on("mouseenter", layerId, (event) => {
        map.getCanvas().style.cursor = "pointer";
        const feature = event.features[0];
        const props = feature.properties;
        const html =
          `<strong>${escapeHtml(props.label)}</strong><br>` +
          `${escapeHtml(bandLabel[props.band] || props.band)}<br>` +
          `${escapeHtml(props.total_text)}`;
        popup.setLngLat(feature.geometry.coordinates).setHTML(html).addTo(map);
      });
      map.on("mouseleave", layerId, () => {
        map.getCanvas().style.cursor = "";
        popup.remove();
      });
    }

    if (featureCollection.features.length) {
      const bounds = new maplibregl.LngLatBounds();
      for (const feature of featureCollection.features) {
        bounds.extend(feature.geometry.coordinates);
      }
      map.fitBounds(bounds, { padding: 60, maxZoom: 5 });
    }
  });
}

// UI-03: read the slider form's own hidden fields plus its current value
// into a plain object matching CompareInputs' own field names — every
// value here is copied straight off a server-rendered form control, never
// computed. Numeric fields are converted from the form's own text values
// to numbers (JSON, not form-encoded, is what /api/v1/compare accepts).
const NUMERIC_FIELDS = [
  "shoot_days_stage",
  "shoot_days_location",
  "crew_size",
  "principal_cast_count",
  "principal_cast_imported_count",
  "crew_imported_count",
  "crew_hired_locally_count",
  "start_index",
];

function collectFormFields(form) {
  const data = new FormData(form);
  const payload = {};
  for (const [key, value] of data.entries()) {
    if (key === "candidate_cities") {
      payload.candidate_cities = payload.candidate_cities || [];
      payload.candidate_cities.push(value);
      continue;
    }
    if (Object.prototype.hasOwnProperty.call(payload, key)) {
      continue; // first occurrence wins — mirrors query-string semantics
    }
    payload[key] = value;
  }
  for (const field of NUMERIC_FIELDS) {
    if (Object.prototype.hasOwnProperty.call(payload, field)) {
      payload[field] = Number(payload[field]);
    }
  }
  return payload;
}

// UI-03: wire the settled-slider live update — independent of whether
// the map itself ever loads (a failed MapLibre CDN load leaves the
// ranked list, and this slider, fully usable per the map's own noscript
// contract above).
function initSlider() {
  const input = document.getElementById(SLIDER_INPUT_ID);
  const form = document.getElementById(SLIDER_FORM_ID);
  const label = document.getElementById(SLIDER_LABEL_ID);
  const rankedContainer = document.getElementById(RANKED_LIST_CONTAINER_ID);
  if (!input || !form || !rankedContainer) {
    return;
  }

  const options = readSliderOptions();
  let settleTimer = null;

  function applyLabel(index) {
    const option = options[Number(index)];
    if (option && label) {
      label.textContent = option.label;
    }
  }

  async function fetchAndApply() {
    const payload = collectFormFields(form);
    const publicPathPrefix = form.getAttribute("action").replace(/\/compare$/, "");
    let response;
    try {
      response = await fetch(`${publicPathPrefix}/api/v1/compare`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    } catch (error) {
      console.error(
        "compare.js: the start-date re-ranking request failed — the last " +
          "server-rendered ranking on this page is unaffected",
        error
      );
      return;
    }
    if (!response.ok) {
      console.error("compare.js: the server refused this start date", response.status);
      return;
    }
    const data = await response.json();
    rankedContainer.innerHTML = data.ranked_list_html;
    updateMapData(data.geojson);
  }

  input.addEventListener("input", () => {
    applyLabel(input.value);
    if (settleTimer) {
      window.clearTimeout(settleTimer);
    }
    settleTimer = window.setTimeout(fetchAndApply, SLIDER_SETTLE_DELAY_MS);
  });

  form.addEventListener("submit", (event) => {
    // JS is active — the debounced fetch above already keeps this page
    // current as the slider moves; a manual "Update" click still works
    // without a full page navigation.
    event.preventDefault();
    if (settleTimer) {
      window.clearTimeout(settleTimer);
    }
    fetchAndApply();
  });
}

async function main() {
  initSlider();

  const container = document.getElementById(MAP_CONTAINER_ID);
  if (!container) {
    return;
  }

  const featureCollection = readGeoJson();
  if (!featureCollection || !Array.isArray(featureCollection.features)) {
    return;
  }

  let maplibregl;
  try {
    maplibregl = await import(MAPLIBRE_MODULE_URL);
  } catch (error) {
    console.error(
      "compare.js: MapLibre did not load from the CDN — the ranked list " +
        "below is the full, server-rendered result and is unaffected",
      error
    );
    return;
  }

  if (!maplibregl || typeof maplibregl.Map !== "function") {
    return;
  }

  buildMap(maplibregl, featureCollection);
}

main();

import {
  LitElement,
  html,
  css,
} from "https://unpkg.com/lit-element@2.4.0/lit-element.js?module";

class LightMapPanel extends LitElement {
  static get properties() {
    return {
      hass: { type: Object },
      narrow: { type: Boolean },
      route: { type: Object },
      panel: { type: Object },
      uploadedSVG: { type: String },
      roomIds: { type: Array },
      lightSensors: { type: Array },
      selectedSensor: { type: Object },
      placedSensors: { type: Object },
    };
  }

  constructor() {
    super();
    this.uploadedSVG = '';
    this.roomIds = [];
    this.lightSensors = [];
    this.selectedSensor = null;
    this.placedSensors = {};
    this.mockTimerInitialized = false;
  }

  updated(changedProperties) {
    if (changedProperties.has('hass')) {
      this.updateLightSensors();
    }
  }

  connectedCallback() {
    super.connectedCallback();

    this.hass.connection.subscribeEvents((event) => {
      console.log(`Event: ${event}`)
      this.handleLightmapUpdate(event.data.svg_path)
    }, "lightmap_update_event")
  }

  handleLightmapUpdate(svg_path) {
    // Access the SVG and render it.
    alert(svg_path)
  }

  updateLightSensors() {
    if (!this.mockTimerInitialized) {
      this.lightSensors = [
        { id: 'sensor.mock_sensor_1', name: 'Mock Sensor 1', state: '150' },
        { id: 'sensor.mock_sensor_2', name: 'Mock Sensor 2', state: '200' },
      ];
      this.mockTimerInitialized = true;

      setTimeout(() => {
        this.lightSensors = [
          { id: 'sensor.mock_sensor_1', name: 'Mock Sensor 1', state: '180' },
          { id: 'sensor.mock_sensor_2', name: 'Mock Sensor 2', state: '250' },
        ];
      }, 60000);
    }
  }

  handleFileUpload(event) {
    const file = event.target.files[0];
    if (file && file.type === "image/svg+xml") {
      const reader = new FileReader();
      reader.onload = (e) => {
        this.uploadedSVG = e.target.result;
        this.extractRoomIds();
      };
      reader.readAsText(file);
    } else {
      alert("Please upload a valid SVG file.");
    }
  }

  extractRoomIds() {
    const parser = new DOMParser();
    const svgDoc = parser.parseFromString(this.uploadedSVG, 'image/svg+xml');
    const roomsGroup = svgDoc.querySelector('#Rooms');

    if (roomsGroup) {
      const roomElements = roomsGroup.querySelectorAll('g[id]');
      this.roomIds = Array.from(roomElements).map((el) => el.id);
    }
  }

  onSensorClick(sensor) {
    if (this.isSensorAlreadyPlaced(sensor.id)) {
      alert("This sensor has already been placed");
      return;
    }
    this.selectedSensor = sensor;
    alert(`Selected sensor: ${sensor.name}`);
  }

  isSensorAlreadyPlaced(sensorId) {
    return Object.values(this.placedSensors).some((sensors) =>
      sensors.some((placedSensor) => placedSensor.id === sensorId)
    );
  }

  getRoomFromCoordinates(x, y) {
    const parser = new DOMParser();
    const svgDoc = parser.parseFromString(this.uploadedSVG, "image/svg+xml");
    const roomsGroup = svgDoc.querySelector("#Rooms");

    if (!roomsGroup) return null;

    const transform = roomsGroup.getAttribute("transform");
    let translateX = 0;
    let translateY = 0;
    if (transform) {
      const match = /translate\((-?\d+\.?\d*),\s*(-?\d+\.?\d*)\)/.exec(transform);
      if (match) {
        translateX = parseFloat(match[1]);
        translateY = parseFloat(match[2]);
      }
    }

    const adjustedX = x - translateX;
    const adjustedY = y - translateY;

    const roomElements = roomsGroup.querySelectorAll("g[id]");
    for (const room of roomElements) {
      const rect = room.querySelector("rect");
      if (!rect) continue;

      const roomX = parseFloat(rect.getAttribute("x"));
      const roomY = parseFloat(rect.getAttribute("y"));
      const roomWidth = parseFloat(rect.getAttribute("width"));
      const roomHeight = parseFloat(rect.getAttribute("height"));

      if (
        adjustedX >= roomX &&
        adjustedY >= roomY &&
        adjustedX <= roomX + roomWidth &&
        adjustedY <= roomY + roomHeight
      ) {
        return room.id;
      }
    }

    return null;
  }

  handleSVGClick(event) {
    if (!this.selectedSensor) {
      alert("Please select a sensor first.");
      return;
    }

    const svgContainer = this.shadowRoot.querySelector(".svg-container svg");
    if (!svgContainer) {
      return;
    }

    //Get the click position in the SVG coordinates
    const point = svgContainer.createSVGPoint();
    point.x = event.clientX;
    point.y = event.clientY;
    const svgPoint = point.matrixTransform(svgContainer.getScreenCTM().inverse());

    const { x, y } = svgPoint;

    //Ensure the placement is inside a room
    const roomId = this.getRoomFromCoordinates(x, y);
    if (!roomId) {
      alert("Sensor placement is outside of any room.");
      return;
    }

    //Check if the sensor is already placed
    if (this.isSensorAlreadyPlaced(this.selectedSensor.id)) {
      alert("This sensor has already been placed.");
      return;
    }

    //Generate a random color for the sensor
    const randomColor = `#${Math.floor(Math.random() * 16777215).toString(16)}`;

    //Add sensor to the placedSensors list
    if (!this.placedSensors[roomId]) {
      this.placedSensors[roomId] = [];
    }
    this.placedSensors[roomId].push({
      ...this.selectedSensor,
      x,
      y,
      color: randomColor,
    });

    //Parse the SVG and add the circle and wavy lines
    const parser = new DOMParser();
    const svgDoc = parser.parseFromString(this.uploadedSVG, "image/svg+xml");

    //Create a group to hold the sensor elements (circle and wavy lines)
    const groupElement = svgDoc.createElementNS("http://www.w3.org/2000/svg", "g");
    groupElement.setAttribute("transform", `translate(${x}, ${y})`);
    groupElement.setAttribute("id", this.selectedSensor.id);

    const circle = svgDoc.createElementNS("http://www.w3.org/2000/svg", "circle");
    circle.setAttribute("cx", 0);
    circle.setAttribute("cy", 0);
    circle.setAttribute("r", "2");
    circle.setAttribute("stroke", randomColor);
    circle.setAttribute("stroke-width", "1");
    circle.setAttribute("fill", "none");

    const wavyLine1 = svgDoc.createElementNS("http://www.w3.org/2000/svg", "path");
    wavyLine1.setAttribute(
      "d",
      "M-1.5 0 Q-1 1, 0 0 Q1 -1, 1.5 0"
    );
    wavyLine1.setAttribute("stroke", randomColor);
    wavyLine1.setAttribute("stroke-width", "1");
    wavyLine1.setAttribute("fill", "none");

    const wavyLine2 = svgDoc.createElementNS("http://www.w3.org/2000/svg", "path");
    wavyLine2.setAttribute(
      "d",
      "M-1.5 0.5 Q-1 1.5, 0 0.5 Q1 -0.5, 1.5 0.5"
    );
    wavyLine2.setAttribute("stroke", randomColor);
    wavyLine2.setAttribute("stroke-width", "1");
    wavyLine2.setAttribute("fill", "none");

    //Append the circle and wavy lines to the group
    groupElement.appendChild(circle);
    groupElement.appendChild(wavyLine1);
    groupElement.appendChild(wavyLine2);

    svgDoc.documentElement.appendChild(groupElement);

    const serializer = new XMLSerializer();
    this.uploadedSVG = serializer.serializeToString(svgDoc);

    this.selectedSensor = null;
    this.requestUpdate();
  }


  removeSensor(roomId, sensorIndex, sensor) {
    this.placedSensors[roomId].splice(sensorIndex, 1);
    if (this.placedSensors[roomId].length === 0) {
      delete this.placedSensors[roomId];
    }

    //Update the SVG to remove the group containing the sensor elements
    const parser = new DOMParser();
    const svgDoc = parser.parseFromString(this.uploadedSVG, "image/svg+xml");

    //Find the group by the sensor ID
    const groupElement = svgDoc.querySelector(`g[id="${sensor.id}"]`);
    if (groupElement) {
      groupElement.remove();
    }

    const serializer = new XMLSerializer();
    this.uploadedSVG = serializer.serializeToString(svgDoc);

    this.requestUpdate();
  }

  render() {
    return html`
      <h1>Light Map Panel</h1>
      <p>Upload an SVG file to display it below:</p>
      <input type="file" @change="${this.handleFileUpload}" accept=".svg" />
      <div style="display: flex; gap: 20px; margin-top: 20px;">
        <div class="svg-container" @click="${this.handleSVGClick}">
          ${this.uploadedSVG
            ? html`<div .innerHTML="${this.uploadedSVG}"></div>`
            : html`<p>No SVG uploaded yet.</p>`}
        </div>
        <div class="room-list">
          <h3>Room List</h3>
          ${this.roomIds.length
            ? html`
                <ul>
                  ${this.roomIds.map(
                    (roomId) => html`
                      <li>
                        ${roomId}
                        <ul>
                          ${(this.placedSensors[roomId] || []).map(
                            (sensor, index) => html`
                              <li>
                                ${sensor.name} (${sensor.x.toFixed(1)}, ${sensor.y.toFixed(1)})
                                <button
                                  @click="${() => this.removeSensor(roomId, index, sensor)}"
                                  style="background: none; border: none; color: red; cursor: pointer;"
                                >
                                  ✖
                                </button>
                              </li>
                            `
                          )}
                        </ul>
                      </li>
                    `
                  )}
                </ul>
              `
            : html`<p>No rooms found in the SVG.</p>`}
        </div>
        <div class="sensor-list">
          <h3>Light Sensors</h3>
          ${this.lightSensors.length
            ? html`
                <ul>
                  ${this.lightSensors.map(
                    (sensor) => {
                      const placedSensor = Object.values(this.placedSensors)
                        .flat()
                        .find((s) => s.id === sensor.id);
                      const sensorColor = placedSensor ? placedSensor.color : "#ccc";

                      return html`
                        <li>
                          <a href="#" @click="${() => this.onSensorClick(sensor)}">
                            <strong>${sensor.name}</strong>
                          </a>: ${sensor.state} lx
                          <span
                            style="display: inline-block; width: 12px; height: 12px; background-color: ${sensorColor}; margin-left: 8px; border: 1px solid #000;"
                          ></span>
                        </li>
                      `;
                    }
                  )}
                </ul>
              `
            : html`<p>No light sensors detected.</p>`}
        </div>
      </div>
    `;
  }

  static get styles() {
    return css`
      :host {
        background-color: #fafafa;
        padding: 16px;
        display: block;
      }
      .svg-container {
        border: 1px solid #ccc;
        padding: 16px;
        background: white;
        max-width: 100%;
        overflow: auto;
      }
      .room-list,
      .sensor-list {
        border: 1px solid #ccc;
        padding: 16px;
        background: white;
        max-width: 200px;
        height: fit-content;
        overflow: auto;
      }
      ul {
        padding-left: 20px;
      }
    `;
  }
}

customElements.define("light-map-panel", LightMapPanel);

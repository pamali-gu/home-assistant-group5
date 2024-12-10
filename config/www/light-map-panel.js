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
    super.updated(changedProperties);
    if (changedProperties.has('hass')) {
      this.updateLightSensors();
    }
  }

  updateLightSensors() {
    if (!this.hass) {
      console.error("hass is not defined");
      return;
    }
    const all_states = Object.values(this.hass.states);
    this.lightSensors = all_states.filter((state) =>
      state.entity_id.startsWith("sensor.") &&
      (
        state.attributes.device_class === "illuminance" ||
        state.attributes.unit_of_measurement === "lux"
      )
    );
  }

  handleFileUpload(event) {
    const file = event.target.files[0];

    if (!this.hass) {
      console.error("hass is not defined");
      return;
    }

    if (file && file.type === "image/svg+xml") {
      const reader = new FileReader();
      reader.onload = (e) => {
        this.uploadedSVG = e.target.result;
        localStorage.setItem("uploadedSVG", this.uploadedSVG);
        this.extractRoomIds();
        this.requestUpdate();

        // Call the shared upload logic
        const formData = this.createFormData(file);
        this.uploadSVG(formData, "Successful File Upload", "SVG uploaded successfully!");
      };
      reader.readAsText(file);
    } else {
      this.hass.callService("persistent_notification", "create", {
        title: "Invalid File",
        message: "Please upload a valid SVG file.",
      });
    }
  }

  reuploadSVG() {
    if (!this.hass) {
      console.error("hass is not defined");
      return;
    }

    try {
      // Parse the SVG to ensure it is valid
      const parser = new DOMParser();
      const svgDoc = parser.parseFromString(this.uploadedSVG, "image/svg+xml");
      const serializer = new XMLSerializer();
      const serializedSVG = serializer.serializeToString(svgDoc);

      // Create the Blob from the properly serialized SVG
      const blob = new Blob([serializedSVG], { type: "image/svg+xml" });

      // Create FormData and upload
      const formData = this.createFormData(blob);
      this.uploadSVG(formData, "SVG Updated", "The SVG has been successfully updated with the new sensor placement.");
    } catch (error) {
      console.error("Error serializing SVG:", error);
    }
  }

  createFormData(file, filename = "Floorplan.svg") {
    const formData = new FormData();
    formData.append("file", file, filename);
    formData.append("media_content_id", "media-source://lightmap/local/uploads/");
    return formData;
  }

  uploadSVG(formData, successTitle, successMessage) {
    fetch("/api/lightmap/storage_handler/upload", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${this.hass.auth.data.access_token}`,
      },
      body: formData,
    })
      .then((response) => {
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
      })
      .then((data) => {
        console.log("SVG upload successful:", data);
        this.hass.callService("persistent_notification", "create", {
          title: successTitle,
          message: successMessage,
        });
      })
      .catch((error) => {
        console.error("Error uploading SVG:", error);
        this.hass.callService("persistent_notification", "create", {
          title: `${successTitle} Failed`,
          message: `Failed to upload the SVG: ${error.message}`,
        });
      });
  }

  connectedCallback() {
    super.connectedCallback();

    const savedSVG = localStorage.getItem("uploadedSVG");
    if (savedSVG) {
      this.uploadedSVG = savedSVG;


      this.requestUpdate().then(() => {
        this.renderPlacedSensors();
        this.extractRoomIds();
      });
    }
    // Restore placed sensors
    const savedPlacedSensors = localStorage.getItem("placedSensors");
    if (savedPlacedSensors) {
      this.placedSensors = JSON.parse(savedPlacedSensors);
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
      this.hass.callService("persistent_notification", "create", {
        title: "Sensor Already Placed",
        message: "This sensor has already been placed.",
      });
      return;
    }
    this.selectedSensor = sensor;
    this.hass.callService("persistent_notification", "create", {
      title: "Sensor Selected:",
      message: `${sensor.attributes?.friendly_name}`,
    });
  }

  isSensorAlreadyPlaced(sensorId) {

    return Object.values(this.placedSensors).some((sensors) =>
      sensors.some((placedSensor) => placedSensor.attributes.unique_id  === sensorId)
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
      this.hass.callService("persistent_notification", "create", {
        title: "No Sensor Selected:",
        message: "Please select a sensor to place.",
      });
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
      this.hass.callService("persistent_notification", "create", {
        title: "Invalid Sensor Placement",
        message: "Sensor placement is outside of any room.",
      });
      return;
    }

    //Check if the sensor is already placed
    if (this.isSensorAlreadyPlaced(this.selectedSensor.attributes?.unique_id)) {
      this.hass.callService("persistent_notification", "create", {
        title: "Sensor Already Placed",
        message: "This sensor has already been placed.",
      });
      return;
    }

    //Generate a random color for the sensor
    const randomColor = `#${Math.floor(Math.random() * 0x7f7f7f).toString(16).padStart(6, '0')}`;

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

    this.savePlacedSensors();
    this.renderPlacedSensors();
    this.selectedSensor = null;
    this.requestUpdate();
  }

  renderPlacedSensors() {
    if (!this.uploadedSVG || !this.placedSensors) {
      return;
    }

    const parser = new DOMParser();
    const svgDoc = parser.parseFromString(this.uploadedSVG, "image/svg+xml");

    // Loop through placed sensors and render them
    for (const [roomId, sensors] of Object.entries(this.placedSensors)) {
      sensors.forEach((sensor) => {

        const existingSensor = svgDoc.querySelector(`g[id="${sensor.attributes.unique_id}"]`);

        // Skip rendering if the sensor already exists
        if (existingSensor) {
          return;
        }

        const groupElement = svgDoc.createElementNS("http://www.w3.org/2000/svg", "g");
        groupElement.setAttribute("transform", `translate(${sensor.x}, ${sensor.y})`);
        groupElement.setAttribute("id", sensor.attributes?.unique_id);

        const circle = svgDoc.createElementNS("http://www.w3.org/2000/svg", "circle");
        circle.setAttribute("cx", 0);
        circle.setAttribute("cy", 0);
        circle.setAttribute("r", "2");
        circle.setAttribute("stroke", sensor.color);
        circle.setAttribute("stroke-width", "1");
        circle.setAttribute("fill", "none");

        const wavyLine1 = svgDoc.createElementNS("http://www.w3.org/2000/svg", "path");
        wavyLine1.setAttribute("d", "M-1.5 0 Q-1 1, 0 0 Q1 -1, 1.5 0");
        wavyLine1.setAttribute("stroke", sensor.color);
        wavyLine1.setAttribute("stroke-width", "1");
        wavyLine1.setAttribute("fill", "none");

        const wavyLine2 = svgDoc.createElementNS("http://www.w3.org/2000/svg", "path");
        wavyLine2.setAttribute("d", "M-1.5 0.5 Q-1 1.5, 0 0.5 Q1 -0.5, 1.5 0.5");
        wavyLine2.setAttribute("stroke", sensor.color);
        wavyLine2.setAttribute("stroke-width", "1");
        wavyLine2.setAttribute("fill", "none");

        // Append elements to the group
        groupElement.appendChild(circle);
        groupElement.appendChild(wavyLine1);
        groupElement.appendChild(wavyLine2);

        // Append group to the SVG
        svgDoc.documentElement.appendChild(groupElement);
      });
    }

    // Serialize the updated SVG and save it
    const serializer = new XMLSerializer();
    this.uploadedSVG = serializer.serializeToString(svgDoc);

    this.reuploadSVG();

    this.selectedSensor = null;
    this.requestUpdate();
  }

  savePlacedSensors() {
    localStorage.setItem("placedSensors", JSON.stringify(this.placedSensors));
  }

  removeSensor(roomId, sensorIndex, sensor) {
    console.log(this.placedSensors);
    this.placedSensors[roomId].splice(sensorIndex, 1);
    if (this.placedSensors[roomId].length === 0) {
      delete this.placedSensors[roomId];
    }
    console.log(this.placedSensors);
    localStorage.setItem("placedSensors", JSON.stringify(this.placedSensors));

    //Update the SVG to remove the group containing the sensor elements
    const parser = new DOMParser();
    const svgDoc = parser.parseFromString(this.uploadedSVG, "image/svg+xml");

    //Find the group by the sensor ID
    const groupElement = svgDoc.querySelector(`g[id="${sensor.attributes?.unique_id}"]`);
    if (groupElement) {
      groupElement.remove();
    }

    const serializer = new XMLSerializer();
    this.uploadedSVG = serializer.serializeToString(svgDoc);
    localStorage.setItem("uploadedSVG", this.uploadedSVG);
    this.reuploadSVG();
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
                            <strong>${sensor.attributes?.friendly_name}</strong>
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
        background-color: var(--card-background-color, #fafafa);
        padding: 16px;
        display: block;
        color: var(--primary-text-color, #000000);
      }
      .svg-container {
        border: 1px solid var(--divider-color, #ccc);
        padding: 16px;
        background: var(--card-background-color, white);
        max-width: 100%;
        overflow: auto;
      }
      .room-list,
      .sensor-list {
        border: 1px solid var(--divider-color, #ccc);
        padding: 16px;
        background: var(--card-background-color, white);
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

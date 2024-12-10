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
      chatHistory: { type: Array },
      chatInput: { type: String },
      isChatOpen: { type: Boolean, reflect: true },
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
    // Chat-related state
    this.chatHistory = [];
    this.chatInput = "";
    this.isChatOpen = false;
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
      const formData = new FormData();
      formData.append("file", file);
      formData.append("media_content_id", "media-source://lightmap/local/uploads/");

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
          console.log("Upload successful:", data);
          this.hass.callService("persistent_notification", "create", {
            title: "Successful File Upload",
            message: "SVG uploaded successfully!",
          });
        })
        .catch((error) => {
          console.error("Error uploading file:", error);
          this.hass.callService("persistent_notification", "create", {
            title: "File Upload Failed",
            message: "Failed to upload the SVG file!",
          });
        });
    } else {
      this.hass.callService("persistent_notification", "create", {
        title: "Invalid File",
        message: "Please upload a valid SVG file.",
      });
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
    alert(`Selected sensor: ${sensor.attributes?.friendly_name}`);
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
  async sendMessageToAPI() {
    try {
      // Send the WebSocket request using hass.callWS
      const data = await this.hass.callWS({
        type: "light-map/plant-info", // The WebSocket message type
        plant_name: this.chatInput, // Payload data
      });
      console.log(data);
      // Handle the response from the WebSocket
      const responseText = data || "No response received";

      // Update chat history with the API response
      this.chatHistory = [
        ...this.chatHistory,
        { user: true, text: this.chatInput },
        { user: false, text: responseText["light_density"] },
      ];

      // Clear the input field
      this.chatInput = "";
    } catch (error) {
      // Handle errors and notify the user
      this.hass.callService("persistent_notification", "create", {
        title: "Error occurred",
        message: `Failed to fetch plant information via WebSocket: ${error.message}`,
      });
    }
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
         <div class="chat-icon" @click="${this.toggleChat}">
          ${this.isChatOpen
      ? html`<i class="fas fa-times"></i>`
      : html`<img src="/local/image/pm_logo.png" alt="Chat" class="icon" />`}
      </div>

      ${this.isChatOpen ? html`
        <div class="chat-panel ${this.isChatOpen ? 'open' : 'closed'}">
          <button class="close-button" @click="${this.toggleChat}">X</button>
          <h3>Suggestions for Plant Placement</h3>
          <div class="chat-history">
            ${this.chatHistory.map(
              (message) => html`
                <p class="${message.user ? 'user-message' : 'bot-message'}">
                  ${message.text}
                </p>
              `
            )}
          </div>
          <input
            type="text"
            .value="${this.chatInput}"
            @input="${(e) => (this.chatInput = e.target.value)}"
            placeholder="Enter a plant name..."
          />
          <button @click="${() => this.sendMessageToAPI(this.chatInput)}">Send</button>
        </div>
      ` : null}
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
      .chat-icon {
        position: absolute;
        bottom: 16px;
        right: 16px;
        padding: 8px;
        border-radius: 50%;
        cursor: pointer;
        background-color: #ffffff;
        font-size: 1.2rem;
        display: flex;
        justify-content: center;
        align-items: center;
        height: 40px;
        width: 40px;
      }
      .icon {
        width: 100%;
        height: 100%;
        object-fit: contain; /* Ensures the image fits well */
      }
      .close-button {
        position: absolute;
        top: 10px;
        right: 10px;
        background: none;
        border: none;
        font-size: 16px;
        cursor: pointer;
        background-color: var(--light-primary-color);
      }
      .chat-panel {
        position: absolute;
        bottom: 0;
        right: 0;
        width: 300px;
        height: 300px;
        background-color: #fff;
        box-shadow: 0px 0px 5px rgba(0, 0, 0, 0.2);
        transition: all 0.3s ease-in-out;
      }
      .chat-panel.open {
        transform: translateY(0);
      }
      .chat-panel.closed {
        transform: translateY(100%);
      }
       .chat-history {
        max-height: 200px;
        overflow-y: auto;
        margin-bottom: 8px;
        border: 1px solid #ccc;
        padding: 8px;
        background: #f9f9f9;
      }
      .user-message {
        text-align: right;
        color: blue;
      }
      .bot-message {
        text-align: left;
        color: green;
      }
      input {
        width: calc(100% - 24px);
        margin-bottom: 8px;
      }
    `;
  }

}

customElements.define("light-map-panel", LightMapPanel);

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
      hasSubmitted: { type: Boolean, reflect: true },
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
    // Plant suggestion related state
    this.chatHistory = [];
    this.chatInput = "";
    this.isChatOpen = false;
    this.hasSubmitted = false;
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

 UploadFromPath(fileContent) {
    if (!this.hass) {
      console.error("hass is not defined");
      return;
    }

    // Check if the content is a valid SVG
    if (!fileContent.endsWith("</svg>")) {
      throw new Error("Invalid SVG content");
    }

    this.uploadedSVG = fileContent;
    localStorage.setItem("uploadedSVG", this.uploadedSVG);
    this.extractRoomIds();
    this.reuploadSVG()
    this.requestUpdate();
  }
  handleLightmapUpdate(svg_data) {
    // Access the SVG and render it.
    this.UploadFromPath(svg_data)
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
    formData.append("media_content_id", "media-source://lightmap/local/uploads");
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
    this.hass.connection.subscribeEvents(event => {
      this.handleLightmapUpdate(event.data.svg)
    }, "lightmap_update_event")
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

        const existingSensor = svgDoc.querySelector(`circle[id="${sensor.attributes.unique_id}"]`);

        // Skip rendering if the sensor already exists
        if (existingSensor) {
          return;
        }

        const groupElement = svgDoc.createElementNS("http://www.w3.org/2000/svg", "g");
        // groupElement.setAttribute("transform", `translate(${}, ${sensor.y})`);
        //groupElement.setAttribute("id", sensor.attributes?.unique_id);

        const circle = svgDoc.createElementNS("http://www.w3.org/2000/svg", "circle");
        circle.setAttribute("id", sensor.attributes?.unique_id);
        circle.setAttribute("cx", sensor.x);
        circle.setAttribute("cy", sensor.y);
        circle.setAttribute("r", "2");
        circle.setAttribute("stroke", sensor.color);
        circle.setAttribute("stroke-width", "1");
        circle.setAttribute("fill", "none");

        const wavyLine1 = svgDoc.createElementNS("http://www.w3.org/2000/svg", "path");
        wavyLine1.setAttribute("d", "M-1.5 0 Q-1 1, 0 0 Q1 -1, 1.5 0");
        wavyLine1.setAttribute("stroke", sensor.color);
        wavyLine1.setAttribute("stroke-width", "0.5");
        wavyLine1.setAttribute("fill", "none");

        const wavyLine2 = svgDoc.createElementNS("http://www.w3.org/2000/svg", "path");
        wavyLine2.setAttribute("d", "M-1.5 0.5 Q-1 1.5, 0 0.5 Q1 -0.5, 1.5 0.5");
        wavyLine2.setAttribute("stroke", sensor.color);
        wavyLine2.setAttribute("stroke-width", "0.5");
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
    this.placedSensors[roomId].splice(sensorIndex, 1);
    if (this.placedSensors[roomId].length === 0) {
      delete this.placedSensors[roomId];
    }
    localStorage.setItem("placedSensors", JSON.stringify(this.placedSensors));

    //Update the SVG to remove the group containing the sensor elements
    const parser = new DOMParser();
    const svgDoc = parser.parseFromString(this.uploadedSVG, "image/svg+xml");

    //Find the group by the sensor ID
    const element = svgDoc.querySelector(`circle[id="${sensor.attributes?.unique_id}"]`);
    if (element && element.parentNode) {
      const parent = element.parentNode;
      parent.remove();
    }

    const radialElement = svgDoc.querySelector(`radialGradient[id="radial-${sensor.attributes?.unique_id}"]`);
    if (radialElement) {
      radialElement.remove();
    }

    const rectElement = svgDoc.querySelector(`rect[id="${sensor.attributes?.unique_id}-rect"]`);
    if (rectElement) {
      rectElement.remove();
    }

    const serializer = new XMLSerializer();
    this.uploadedSVG = serializer.serializeToString(svgDoc);
    localStorage.setItem("uploadedSVG", this.uploadedSVG);
    this.reuploadSVG();
    this.requestUpdate();
  }

  toggleChat() {
    this.isChatOpen = !this.isChatOpen;
  }

  async sendMessageToAPI() {
    try {
      // Send the WebSocket request using hass.callWS
      const data = await this.hass.callWS({
        type: "light-map/plant-info", // The WebSocket message type
        plant_name: this.chatInput, // Payload data
      });
      // Handle the response from the WebSocket
      const responseText = data || "No response received";
      const lightDensity = responseText["light_density"];
      const message = responseText["message"];
      const sensorList = responseText["sensors"];
      let sensorDetails = "";

      if (Object.keys(sensorList).length === 0 && lightDensity !== "INVALID") {
        sensorDetails = `Your "${this.chatInput}" plant needs "${lightDensity}" level of light density.
          There are no suitable sensors to place at the moment.`;
      } else if (message.toUpperCase().trim() === "INVALID PLANT NAME") {
        sensorDetails = `Invalid plant name. Please check and try again.`;
      } else {
        // Collect friendly names of the sensors with their light density
        const suggestions = Object.entries(sensorList).map(([sensorId]) => {
          const sensor = this.lightSensors.find(
            (s) => s.entity_id === sensorId
          );
          const friendlyName = sensor
            ? sensor.attributes?.friendly_name
            : sensorId;
          return `${friendlyName},`;
        });

        sensorDetails = `Your "${this.chatInput}" plant needs "${lightDensity}" level of light density.
          You can place the plant near the following sensors: \n ${suggestions.join("\n")}`;
      }

      // Update chat history with the API response
      this.chatHistory = [
        ...this.chatHistory,
        { user: true, text: this.chatInput },
        { user: false, text: sensorDetails },
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

      ${this.isChatOpen
        ? html`
            <div class="chat-panel ${this.isChatOpen ? "open" : "closed"}">
              <button class="close-button" @click="${this.toggleChat}">X</button>
              <h3>Suggestions for Plant Placement</h3>
              ${this.hasSubmitted
                ? html`
                    <div class="chat-history">
                      ${this.chatHistory.map(
                        (message) => html`
                          <p
                            class="${message.user
                              ? "user-message"
                              : "bot-message"}">
                            ${message.text}
                          </p>
                        `
                      )}
                    </div>
                  `
                : null}
              <input
                type="text"
                class="search-field"
                .value="${this.chatInput}"
                @input="${(e) => (this.chatInput = e.target.value)}"
                placeholder="Enter a plant name..."
              />
              <button
                class="send-button"
                @click="${() => {
                  this.sendMessageToAPI(this.chatInput);
                  this.hasSubmitted = true;
                }}">
                Send
              </button>
            </div>
          `
        : null}
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
        position: fixed;
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
        background-color: var(white, --card-background-color);
      }
      .send-button {
        background-color: var(--primary-color, #007bff);
        color: var(--button-text-color, white);
        border: none;
        padding: 12px 12px;
        font-size: 14px;
        border-radius: 4px;
        cursor: pointer;
        width: 60%;
        float: right;
        transition: background-color 0.3s ease, transform 0.2s ease;
      }
      .search-field {
        width: 90%;
        padding: 15px 12px;
        font-size: 14px;
        border: 1px solid #ccc;
        border-radius: 4px;
        outline: none;
        transition: border-color 0.3s ease, box-shadow 0.3s ease;
      }
      .chat-panel {
        border: 1px solid #ccc;
        padding: 16px;
        position: fixed;
        bottom: 0;
        right: 0;
        max-width: 300px;
        height: fit-content;
        overflow: auto;
        background-color: var(--card-background-color, white);
        box-shadow: 0px 0px 5px rgba(0, 0, 0, 0.2);
        border-radius: 10px;
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
        background: var(--card-background-color, white);
      }
      .user-message {
        text-align: right;
        color: var(--primary-color, #007bff);
      }
      .bot-message {
        text-align: left;
        color: #4fe14f;
      }
      input {
        width: calc(100% - 24px);
        margin-bottom: 8px;
      }
    `;
  }

}

customElements.define("light-map-panel", LightMapPanel);
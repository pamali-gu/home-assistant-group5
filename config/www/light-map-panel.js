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
    };
  }

  constructor() {
    super();
    this.uploadedSVG = '';
    this.roomIds = [];
  }
  //Upload svg and parse
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

  // Extract room IDs from the SVG content
  extractRoomIds() {
    const parser = new DOMParser();
    const svgDoc = parser.parseFromString(this.uploadedSVG, 'image/svg+xml');
    const roomsGroup = svgDoc.querySelector('#Rooms');

    if (roomsGroup) {
      const roomElements = roomsGroup.querySelectorAll('g[id]');
      this.roomIds = Array.from(roomElements).map((el) => el.id);
    }
  }

  render() {
    return html`
      <h1>Light Map Panel</h1>
      <p>Upload an SVG file to display it below:</p>
      <input type="file" @change="${this.handleFileUpload}" accept=".svg" />
      <div style="display: flex; gap: 20px; margin-top: 20px;">
        <div class="svg-container">
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
                    (roomId) => html`<li>${roomId}</li>`
                  )}
                </ul>`
            : html`<p>No rooms found in the SVG.</p>`}
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
      .room-list {
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

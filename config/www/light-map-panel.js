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
      };
    }

    // Empty render method for now
    render() {
      return html`
        <h1>Light Map Panel</h1>
        <p>This is a custom panel (empty for now).</p>
      `;
    }

    static get styles() {
      return css`
        :host {
          background-color: #fafafa;
          padding: 16px;
          display: block;
        }
      `;
    }
  }

  customElements.define("light-map-panel", LightMapPanel);

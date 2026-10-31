// Sidebar panel for UniFi People Pointer.
// Embeds the web UI that the integration serves on its own port (all
// interfaces) and hands the current Home Assistant access token to it.

const AUTH_REQUEST = "upp-auth-request";
const AUTH_MESSAGE = "upp-auth";

class UniFiPeoplePointerPanel extends HTMLElement {
  constructor() {
    super();
    this._onMessage = this._onMessage.bind(this);
    this.attachShadow({ mode: "open" });
  }

  set hass(hass) {
    const previous = this._hass;
    this._hass = hass;
    if (this._menuButton) {
      this._menuButton.hass = hass;
    }
    if (!previous || previous.auth?.data?.access_token !== hass.auth?.data?.access_token) {
      this._sendToken();
    }
  }

  set narrow(narrow) {
    this._narrow = narrow;
    if (this._menuButton) {
      this._menuButton.narrow = narrow;
    }
  }

  set panel(panel) {
    const port = panel?.config?.port;
    if (port !== this._port) {
      this._port = port;
      this._render();
    }
  }

  connectedCallback() {
    window.addEventListener("message", this._onMessage);
    this._render();
  }

  disconnectedCallback() {
    window.removeEventListener("message", this._onMessage);
  }

  get _uiUrl() {
    // Same host the browser uses for Home Assistant, the UI's own port.
    const host = window.location.hostname.includes(":")
      ? `[${window.location.hostname}]`
      : window.location.hostname;
    return `http://${host}:${this._port}/`;
  }

  get _uiOrigin() {
    return new URL(this._uiUrl).origin;
  }

  _render() {
    if (!this.isConnected || !this._port) {
      return;
    }
    const blocked = window.location.protocol === "https:";
    this.shadowRoot.innerHTML = `
      <style>
        :host { display: flex; flex-direction: column; height: 100%; background: var(--primary-background-color);
          font-family: var(--ha-font-family-body, var(--paper-font-body1_-_font-family, Roboto, "Noto Sans", sans-serif)); }
        .toolbar { display: flex; align-items: center; height: var(--header-height, 56px); padding: 0 12px;
          background: var(--app-header-background-color, var(--primary-color)); color: var(--app-header-text-color, #fff);
          font-size: 20px; box-sizing: border-box; flex: 0 0 auto; gap: 8px; }
        iframe { border: 0; width: 100%; flex: 1 1 auto; display: block; }
        .notice { margin: 24px auto; max-width: 560px; padding: 24px; border-radius: 12px;
          background: var(--card-background-color); color: var(--primary-text-color); line-height: 1.5; }
        .notice a { color: var(--primary-color); font-weight: 500; }
      </style>
      <div class="toolbar"><ha-menu-button></ha-menu-button><span>UniFi People Pointer</span></div>
      ${blocked
        ? `<div class="notice">
             <p>Home Assistant is open over HTTPS. The browser does not embed the
             People Pointer web UI, which is served over plain HTTP on port ${this._port}.</p>
             <p><a href="${this._uiUrl}" target="_blank" rel="noopener">Open the web UI in a new tab</a></p>
           </div>`
        : `<iframe src="${this._uiUrl}" title="UniFi People Pointer"></iframe>`}
    `;
    this._menuButton = this.shadowRoot.querySelector("ha-menu-button");
    this._menuButton.hass = this._hass;
    this._menuButton.narrow = this._narrow;
    this._iframe = this.shadowRoot.querySelector("iframe");
    this._iframeLoaded = false;
    if (this._iframe) {
      this._iframe.addEventListener("load", () => {
        this._iframeLoaded = true;
        this._sendToken();
      });
    }
  }

  async _token() {
    const auth = this._hass?.auth;
    if (!auth) {
      return null;
    }
    if (auth.expired && typeof auth.refreshAccessToken === "function") {
      await auth.refreshAccessToken();
    }
    return auth.data?.access_token || auth.accessToken || null;
  }

  async _sendToken() {
    // Before the first load the frame still holds about:blank (our origin).
    if (!this._iframeLoaded || !this._port) {
      return;
    }
    const token = await this._token();
    const target = this._iframe?.contentWindow;
    if (token && target) {
      target.postMessage({ type: AUTH_MESSAGE, token }, this._uiOrigin);
    }
  }

  _onMessage(event) {
    if (!this._iframe || event.source !== this._iframe.contentWindow) {
      return;
    }
    if (event.origin === this._uiOrigin && event.data?.type === AUTH_REQUEST) {
      this._sendToken();
    }
  }
}

if (!customElements.get("unifi-people-pointer-panel")) {
  customElements.define("unifi-people-pointer-panel", UniFiPeoplePointerPanel);
}

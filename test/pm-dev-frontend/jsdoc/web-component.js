// Test case: Web Component with custom elements
// This tests the agent's ability to handle web component documentation patterns

/**
 * Custom button web component.
 * @element cui-button
 * @fires click - Fired when button is clicked
 * @fires focus - Fired when button receives focus
 * @slot - Default slot for button content
 * @slot icon - Slot for button icon
 * @csspart button - The button element
 * @cssprop --button-bg-color - Button background color
 * @cssprop --button-text-color - Button text color
 */
class CuiButton extends HTMLElement {
    /**
     * Observed attributes for the component.
     * @returns {string[]} List of observed attribute names
     */
    static get observedAttributes() {
        return ['disabled', 'variant', 'size'];
    }

    /**
     * Creates a new CuiButton instance.
     */
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
    }

    /**
     * Called when element is connected to DOM.
     */
    connectedCallback() {
        this.render();
    }

    /**
     * Called when an observed attribute changes.
     * @param {string} name - Attribute name
     * @param {string|null} oldValue - Previous value
     * @param {string|null} newValue - New value
     */
    attributeChangedCallback(name, oldValue, newValue) {
        if (oldValue !== newValue) {
            this.render();
        }
    }

    /**
     * Renders the component.
     * @private
     */
    render() {
        this.shadowRoot.innerHTML = `
            <style>
                :host { display: inline-block; }
                button {
                    background: var(--button-bg-color, #007bff);
                    color: var(--button-text-color, white);
                }
            </style>
            <button part="button">
                <slot name="icon"></slot>
                <slot></slot>
            </button>
        `;
    }
}

customElements.define('cui-button', CuiButton);

export { CuiButton };

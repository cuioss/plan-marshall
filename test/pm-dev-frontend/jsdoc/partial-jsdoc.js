/**
 * @fileoverview Configuration module for application settings.
 * @module config
 */

/**
 * Application configuration class.
 * @class
 */
class AppConfig {
    /**
     * Creates a new AppConfig instance.
     * Missing: @param documentation
     */
    constructor(options) {
        this.settings = options;
    }

    /**
     * Gets a configuration value.
     * @param {string} key - The configuration key
     * Missing: @returns, @throws
     */
    get(key) {
        if (!key) {
            throw new Error('Key is required');
        }
        return this.settings[key];
    }

    // Missing entire JSDoc block
    set(key, value) {
        this.settings[key] = value;
    }

    /**
     * Checks if a key exists.
     * @param key Missing type annotation
     * @returns {boolean} True if key exists
     */
    has(key) {
        return key in this.settings;
    }
}

/**
 * Loads configuration from environment.
 * Missing: @returns type, @example
 */
function loadFromEnv() {
    return {
        apiUrl: process.env.API_URL,
        debug: process.env.DEBUG === 'true'
    };
}

/**
 * Merges two configuration objects.
 * @param base - Missing type
 * @param overrides - Missing type
 */
function mergeConfig(base, overrides) {
    return { ...base, ...overrides };
}

export { AppConfig, loadFromEnv, mergeConfig };

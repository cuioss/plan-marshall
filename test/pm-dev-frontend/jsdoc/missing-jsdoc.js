// Missing @fileoverview
// Missing @module

// Missing class documentation
class DataProcessor {
    // Missing constructor documentation
    constructor(config) {
        this.config = config;
        this.data = [];
    }

    // Missing method documentation
    async processData(input) {
        const result = await this.transform(input);
        return this.validate(result);
    }

    // Incomplete JSDoc - missing @returns
    /**
     * Transforms input data.
     * @param {Object} data - Input data
     */
    transform(data) {
        return { ...data, processed: true };
    }

    // Missing JSDoc entirely
    validate(data) {
        if (!data) return false;
        return data.processed === true;
    }

    // Incomplete JSDoc - missing @param types
    /**
     * Filters the data based on criteria.
     * @param criteria - The filter criteria
     */
    filter(criteria) {
        return this.data.filter(item => item.matches(criteria));
    }
}

// Missing function documentation
function calculateSum(numbers) {
    return numbers.reduce((sum, num) => sum + num, 0);
}

// Incomplete JSDoc - missing @example
/**
 * Formats a date string.
 * @param {Date} date - The date to format
 * @returns {string} Formatted date string
 */
function formatDate(date) {
    return date.toISOString().split('T')[0];
}

// Missing @typedef for complex object
const defaultConfig = {
    timeout: 5000,
    retries: 3,
    baseUrl: '/api'
};

// Arrow function missing documentation
const multiply = (a, b) => a * b;

// Missing @callback documentation
const handlers = {
    onSuccess: (data) => console.log(data),
    onError: (err) => console.error(err)
};

// Incorrect JSDoc - @param name doesn't match
/**
 * Gets an item by ID.
 * @param {string} itemId - The item identifier
 */
function getById(id) {
    return fetch(`/api/items/${id}`);
}

// Missing @throws documentation
/**
 * Parses JSON safely.
 * @param {string} jsonString - The JSON string to parse
 * @returns {Object} Parsed object
 */
function parseJson(jsonString) {
    try {
        return JSON.parse(jsonString);
    } catch (e) {
        throw new Error(`Invalid JSON: ${e.message}`);
    }
}

// Missing @async tag
/**
 * Fetches user data.
 * @param {string} userId - User ID
 * @returns {Promise<Object>} User data
 */
async function fetchUser(userId) {
    const response = await fetch(`/api/users/${userId}`);
    return response.json();
}

export { DataProcessor, calculateSum, formatDate, multiply, getById, parseJson, fetchUser };

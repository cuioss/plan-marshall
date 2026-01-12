/**
 * @fileoverview User management module for handling user operations.
 * @module utils/user-manager
 */

/**
 * Represents a user in the system.
 * @typedef {Object} User
 * @property {string} id - Unique identifier
 * @property {string} name - User's display name
 * @property {string} email - User's email address
 * @property {Date} createdAt - Account creation date
 */

/**
 * User manager class for CRUD operations.
 * @class UserManager
 * @example
 * const manager = new UserManager();
 * const user = await manager.getUser('123');
 */
class UserManager {
    /**
     * Creates an instance of UserManager.
     * @param {Object} [options={}] - Configuration options
     * @param {string} [options.apiUrl] - API endpoint URL
     * @param {number} [options.timeout=5000] - Request timeout in milliseconds
     */
    constructor(options = {}) {
        this.apiUrl = options.apiUrl || '/api/users';
        this.timeout = options.timeout || 5000;
    }

    /**
     * Retrieves a user by their unique identifier.
     * @param {string} userId - The unique identifier of the user
     * @returns {Promise<User>} The user object
     * @throws {Error} If the user is not found
     * @example
     * const user = await manager.getUser('user-123');
     * console.log(user.name);
     */
    async getUser(userId) {
        const response = await fetch(`${this.apiUrl}/${userId}`);
        if (!response.ok) {
            throw new Error(`User not found: ${userId}`);
        }
        return response.json();
    }

    /**
     * Creates a new user in the system.
     * @param {Object} userData - The user data to create
     * @param {string} userData.name - User's display name
     * @param {string} userData.email - User's email address
     * @returns {Promise<User>} The created user object
     */
    async createUser(userData) {
        const response = await fetch(this.apiUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(userData)
        });
        return response.json();
    }

    /**
     * Updates an existing user.
     * @param {string} userId - The unique identifier of the user
     * @param {Partial<User>} updates - The fields to update
     * @returns {Promise<User>} The updated user object
     */
    async updateUser(userId, updates) {
        const response = await fetch(`${this.apiUrl}/${userId}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(updates)
        });
        return response.json();
    }

    /**
     * Deletes a user from the system.
     * @param {string} userId - The unique identifier of the user to delete
     * @returns {Promise<boolean>} True if deletion was successful
     */
    async deleteUser(userId) {
        const response = await fetch(`${this.apiUrl}/${userId}`, {
            method: 'DELETE'
        });
        return response.ok;
    }
}

/**
 * Validates an email address format.
 * @param {string} email - The email address to validate
 * @returns {boolean} True if the email is valid
 * @example
 * validateEmail('user@example.com'); // true
 * validateEmail('invalid-email'); // false
 */
function validateEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

/**
 * Formats a user's full name.
 * @param {string} firstName - User's first name
 * @param {string} lastName - User's last name
 * @param {Object} [options] - Formatting options
 * @param {boolean} [options.uppercase=false] - Whether to uppercase the result
 * @returns {string} The formatted full name
 */
function formatFullName(firstName, lastName, options = {}) {
    const fullName = `${firstName} ${lastName}`;
    return options.uppercase ? fullName.toUpperCase() : fullName;
}

export { UserManager, validateEmail, formatFullName };

/**
 * Cookie utilities for anonymous user tracking
 */

/**
 * Generate a unique user ID
 */
function generateUserId(): string {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Get or create aguai_uid cookie
 * This cookie is used for anonymous user tracking and quota management
 */
export function getOrCreateUserId(): string {
    const cookieName = 'aguai_uid';

    // Try to get existing cookie
    const cookies = document.cookie.split(';');
    for (const cookie of cookies) {
        const [name, value] = cookie.trim().split('=');
        if (name === cookieName && value) {
            return value;
        }
    }

    // Create new user ID
    const userId = generateUserId();

    // Set cookie (expires in 1 year)
    const expires = new Date();
    expires.setFullYear(expires.getFullYear() + 1);
    document.cookie = `${cookieName}=${userId}; expires=${expires.toUTCString()}; path=/; SameSite=Lax`;

    return userId;
}

/**
 * Get aguai_uid cookie value
 */
export function getUserId(): string | null {
    const cookieName = 'aguai_uid';
    const cookies = document.cookie.split(';');

    for (const cookie of cookies) {
        const [name, value] = cookie.trim().split('=');
        if (name === cookieName && value) {
            return value;
        }
    }

    return null;
}

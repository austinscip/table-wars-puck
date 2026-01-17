/**
 * Universal Game State Validator
 * Prevents crashes from invalid/incomplete state objects
 *
 * Sprint 1D: Game Polish & Bug Fixes
 *
 * Usage:
 * const validator = new GameStateValidator(['score', 'lives', 'game_over']);
 * if (validator.validate(state)) {
 *     // Safe to use state
 * }
 */

class GameStateValidator {
    constructor(requiredFields = []) {
        this.requiredFields = requiredFields;
        this.optionalFields = [];
        this.typeChecks = {};
        this.rangeChecks = {};
    }

    /**
     * Add optional fields (won't fail validation if missing)
     */
    withOptional(fields) {
        this.optionalFields = fields;
        return this;
    }

    /**
     * Add type checking for specific fields
     * Example: withTypes({ score: 'number', name: 'string', active: 'boolean' })
     */
    withTypes(types) {
        this.typeChecks = types;
        return this;
    }

    /**
     * Add range validation for numeric fields
     * Example: withRanges({ score: [0, 10000], lives: [0, 5] })
     */
    withRanges(ranges) {
        this.rangeChecks = ranges;
        return this;
    }

    /**
     * Validate a state object
     * Returns true if valid, false otherwise
     * Logs warnings for missing/invalid fields
     */
    validate(state) {
        if (!state || typeof state !== 'object') {
            console.error('[GameStateValidator] State is not an object:', state);
            return false;
        }

        let isValid = true;

        // Check required fields
        for (const field of this.requiredFields) {
            if (!(field in state)) {
                console.warn(`[GameStateValidator] Missing required field: ${field}`);
                isValid = false;
            }
        }

        // Type checking
        for (const [field, expectedType] of Object.entries(this.typeChecks)) {
            if (field in state) {
                const actualType = typeof state[field];
                if (actualType !== expectedType) {
                    console.warn(`[GameStateValidator] Type mismatch for ${field}: expected ${expectedType}, got ${actualType}`);
                    isValid = false;
                }
            }
        }

        // Range checking
        for (const [field, [min, max]] of Object.entries(this.rangeChecks)) {
            if (field in state && typeof state[field] === 'number') {
                if (state[field] < min || state[field] > max) {
                    console.warn(`[GameStateValidator] Range violation for ${field}: ${state[field]} not in [${min}, ${max}]`);
                    isValid = false;
                }
            }
        }

        return isValid;
    }

    /**
     * Sanitize a state object by providing defaults for missing fields
     * Returns a new object with defaults applied
     */
    sanitize(state, defaults = {}) {
        if (!state || typeof state !== 'object') {
            console.error('[GameStateValidator] Cannot sanitize non-object:', state);
            return defaults;
        }

        const sanitized = { ...state };

        // Apply defaults for missing required fields
        for (const field of this.requiredFields) {
            if (!(field in sanitized) && field in defaults) {
                sanitized[field] = defaults[field];
                console.warn(`[GameStateValidator] Applied default for ${field}: ${defaults[field]}`);
            }
        }

        // Clamp numeric fields to ranges
        for (const [field, [min, max]] of Object.entries(this.rangeChecks)) {
            if (field in sanitized && typeof sanitized[field] === 'number') {
                sanitized[field] = Math.max(min, Math.min(max, sanitized[field]));
            }
        }

        return sanitized;
    }

    /**
     * Validate and throw error if invalid
     * Use this for critical validation where game cannot continue without valid state
     */
    validateOrThrow(state) {
        if (!this.validate(state)) {
            throw new Error('Invalid game state received');
        }
        return true;
    }
}

// ============================================================================
// COMMON VALIDATORS FOR DIFFERENT GAME TYPES
// ============================================================================

/**
 * Validator for single-player score-based games
 */
const SinglePlayerValidator = new GameStateValidator(['score', 'game_over'])
    .withTypes({ score: 'number', game_over: 'boolean' })
    .withRanges({ score: [0, 1000000] })
    .withOptional(['lives', 'time_remaining', 'level', 'combo']);

/**
 * Validator for multiplayer games
 */
const MultiplayerValidator = new GameStateValidator(['players', 'game_over'])
    .withTypes({ players: 'object', game_over: 'boolean' })
    .withOptional(['current_turn', 'time_remaining', 'round']);

/**
 * Validator for time-based games
 */
const TimeBasedValidator = new GameStateValidator(['time_remaining', 'score', 'game_over'])
    .withTypes({ time_remaining: 'number', score: 'number', game_over: 'boolean' })
    .withRanges({ time_remaining: [0, 3600], score: [0, 1000000] })
    .withOptional(['lives', 'level']);

/**
 * Validator for 3D racing games
 */
const RacingValidator = new GameStateValidator(['position', 'speed', 'score', 'game_over'])
    .withTypes({ position: 'object', speed: 'number', score: 'number', game_over: 'boolean' })
    .withRanges({ speed: [0, 500], score: [0, 1000000] })
    .withOptional(['nitro', 'crashes', 'collectibles']);

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

/**
 * Safe property access with default value
 * Example: safeGet(state, 'player.position.x', 0)
 */
function safeGet(obj, path, defaultValue = null) {
    const keys = path.split('.');
    let current = obj;

    for (const key of keys) {
        if (current && typeof current === 'object' && key in current) {
            current = current[key];
        } else {
            return defaultValue;
        }
    }

    return current !== undefined ? current : defaultValue;
}

/**
 * Ensure a number is within a range
 */
function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
}

/**
 * Safe number conversion
 */
function toNumber(value, defaultValue = 0) {
    const num = Number(value);
    return isNaN(num) ? defaultValue : num;
}

/**
 * Safe array check
 */
function isValidArray(value) {
    return Array.isArray(value) && value.length > 0;
}

// Export for use in game templates
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        GameStateValidator,
        SinglePlayerValidator,
        MultiplayerValidator,
        TimeBasedValidator,
        RacingValidator,
        safeGet,
        clamp,
        toNumber,
        isValidArray
    };
}

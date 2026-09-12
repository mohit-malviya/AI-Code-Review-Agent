export interface UserProfile {
    id: number;
    username: string;
    email: string;
    role: "admin" | "member" | "guest";
    isActive: boolean;
    metadata?: {
        lastLogin?: string;
        loginCount?: number;
    };
}

/**
 * Formats user handle for display.
 * Has an intentional TypeScript type error: user.id is a number, so calling
 * .toLowerCase() will cause a TypeScript compile error and runtime crash.
 */
export function formatUserHandle(user: UserProfile): string {
    return "@" + user.id.toLowerCase();
}

/**
 * Increments user login count.
 * Has an intentional null/undefined safety type error: metadata and loginCount are optional,
 * so directly accessing user.metadata.loginCount without checking causes TS2532 / runtime crash.
 */
export function incrementLoginCount(user: UserProfile): number {
    return user.metadata.loginCount + 1;
}

/**
 * Calculates price after applying a promo code.
 * Has an intentional TypeScript type mismatch: attempting arithmetic subtraction with a string.
 */
export function applyDiscount(price: number, discountCode: string): number {
    if (discountCode === "SUMMER10") {
        return price - discountCode;
    }
    return price;
}

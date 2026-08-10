export type OperationalState = "Success" | "Warning" | "Error" | "Running" | "Neutral";

export interface OperationalResult {
    status: OperationalState;
    platformCode: string;
    vendorCode?: string;
    message: string;
    recommendedAction: string;
}

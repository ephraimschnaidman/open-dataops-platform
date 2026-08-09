export type OperationalState = "Success" | "Warning" | "Error";

export interface OperationalResult {
    status: OperationalState;
    platformCode: string;
    vendorCode?: string;
    message: string;
    recommendedAction: string;
}

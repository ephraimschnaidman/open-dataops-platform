"use client";

import { useEffect, useSyncExternalStore } from "react";

export const environments = ["Production", "Staging", "Development"] as const;
export type Environment = (typeof environments)[number];

const CURRENT_KEY = "datum.current-environment";
const DEFAULT_KEY = "datum.default-environment";

let currentEnvironment: Environment = "Production";
let defaultEnvironment: Environment = "Production";
let hydrated = false;
let snapshot: { currentEnvironment: Environment; defaultEnvironment: Environment } = { currentEnvironment, defaultEnvironment };
const listeners = new Set<() => void>();

export function isEnvironment(value: string | null): value is Environment {
    return environments.includes(value as Environment);
}

function publish() {
    snapshot = { currentEnvironment, defaultEnvironment };
    listeners.forEach((listener) => listener());
}

function hydrate() {
    if (hydrated || typeof window === "undefined") return;
    hydrated = true;
    const savedDefault = window.sessionStorage.getItem(DEFAULT_KEY);
    const savedCurrent = window.sessionStorage.getItem(CURRENT_KEY);
    if (isEnvironment(savedDefault)) defaultEnvironment = savedDefault;
    currentEnvironment = isEnvironment(savedCurrent) ? savedCurrent : defaultEnvironment;
    publish();
}

function subscribe(listener: () => void) {
    listeners.add(listener);
    return () => listeners.delete(listener);
}

export function useEnvironmentContext() {
    const state = useSyncExternalStore(subscribe, () => snapshot, () => snapshot);
    useEffect(hydrate, []);

    return {
        ...state,
        setCurrentEnvironment(value: Environment) {
            currentEnvironment = value;
            if (typeof window !== "undefined") window.sessionStorage.setItem(CURRENT_KEY, value);
            publish();
        },
        setDefaultEnvironment(value: Environment) {
            defaultEnvironment = value;
            if (typeof window !== "undefined") window.sessionStorage.setItem(DEFAULT_KEY, value);
            publish();
        },
    };
}

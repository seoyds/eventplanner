export async function register() {
  // Polyfill CustomEvent for Node.js SSR environment (needed by CopilotKit)
  if (typeof globalThis.CustomEvent === 'undefined') {
    (globalThis as any).CustomEvent = class CustomEvent extends Event {
      public detail: any;
      constructor(event: string, params: any = {}) {
        super(event, params);
        this.detail = params.detail ?? null;
      }
    };
  }
}

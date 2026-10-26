export function mockFetch(routes) {
  const fetchMock = vi.fn(async (url, options = {}) => {
    const entry = routes.find((route) =>
      typeof route.match === "string" ? url.includes(route.match) : route.match(url, options)
    );
    if (!entry) {
      throw new Error(`No mock route for ${options.method ?? "GET"} ${url}`);
    }
    if (entry.fail) {
      return {
        ok: false,
        status: entry.status ?? 500,
        statusText: "Error",
        json: async () => entry.payload ?? { detail: entry.message ?? "Request failed" },
      };
    }
    return {
      ok: true,
      status: 200,
      json: async () => (typeof entry.data === "function" ? entry.data(options) : entry.data),
    };
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

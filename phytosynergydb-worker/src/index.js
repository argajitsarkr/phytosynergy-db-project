const DOWN_STATUSES = new Set([0, 502, 503, 504, 521, 522, 523, 524, 530]);

export default {
  async fetch(request, env) {
    try {
      const response = await fetch(request);
      if (DOWN_STATUSES.has(response.status)) {
        return Response.redirect(env.FALLBACK_URL, 302);
      }
      return response;
    } catch {
      return Response.redirect(env.FALLBACK_URL, 302);
    }
  },
};

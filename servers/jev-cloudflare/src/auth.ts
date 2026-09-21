export type AuthorizationResult =
  | { authorized: true }
  | { authorized: false; response: Response };

const encoder = new TextEncoder();

function jsonError(status: number, error: string, headers: HeadersInit = {}): Response {
  return Response.json(
    { error },
    {
      status,
      headers: {
        "cache-control": "no-store",
        ...headers,
      },
    },
  );
}

async function constantTimeEqual(left: string, right: string): Promise<boolean> {
  const [leftDigest, rightDigest] = await Promise.all([
    crypto.subtle.digest("SHA-256", encoder.encode(left)),
    crypto.subtle.digest("SHA-256", encoder.encode(right)),
  ]);

  const leftBytes = new Uint8Array(leftDigest);
  const rightBytes = new Uint8Array(rightDigest);
  let difference = leftBytes.length ^ rightBytes.length;

  const length = Math.max(leftBytes.length, rightBytes.length);
  for (let index = 0; index < length; index += 1) {
    difference |= (leftBytes[index] ?? 0) ^ (rightBytes[index] ?? 0);
  }

  return difference === 0;
}

export async function authorizeMcpRequest(
  request: Request,
  configuredToken: string | undefined,
): Promise<AuthorizationResult> {
  const expectedToken = configuredToken?.trim();

  if (!expectedToken) {
    return {
      authorized: false,
      response: jsonError(503, "MCP authentication is not configured."),
    };
  }

  const authorization = request.headers.get("authorization");
  if (!authorization?.startsWith("Bearer ")) {
    return {
      authorized: false,
      response: jsonError(401, "Unauthorized.", {
        "www-authenticate": 'Bearer realm="jev-cloudflare-mcp"',
      }),
    };
  }

  const suppliedToken = authorization.slice("Bearer ".length);
  if (!(await constantTimeEqual(suppliedToken, expectedToken))) {
    return {
      authorized: false,
      response: jsonError(401, "Unauthorized.", {
        "www-authenticate": 'Bearer realm="jev-cloudflare-mcp"',
      }),
    };
  }

  return { authorized: true };
}

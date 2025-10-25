import { NextRequest } from "next/server";

export async function GET(
  request: NextRequest,
  { params }: { params: { jobId: string } }
) {
  const { jobId } = params;

  // Get the backend API URL from environment or use default
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8088";
  const backendUrl = `${apiUrl}/api/sse/generations/${jobId}/progress`;

  try {
    // Forward the request to the backend SSE endpoint
    const backendResponse = await fetch(backendUrl, {
      method: "GET",
      headers: {
        // Forward relevant headers from the original request
        ...(request.headers.get("authorization") && {
          Authorization: request.headers.get("authorization")!,
        }),
        ...(request.headers.get("x-tenant") && {
          "X-Tenant": request.headers.get("x-tenant")!,
        }),
      },
      signal: request.signal,
    });

    if (!backendResponse.ok) {
      return new Response(`Backend SSE error: ${backendResponse.statusText}`, {
        status: backendResponse.status,
      });
    }

    // Stream the backend response directly to the client
    return new Response(backendResponse.body, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        Connection: "keep-alive",
      },
    });
  } catch (error) {
    console.error("SSE proxy error:", error);
    return new Response("SSE connection failed", { status: 500 });
  }
}

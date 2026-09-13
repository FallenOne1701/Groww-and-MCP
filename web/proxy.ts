import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { accessCookieName, accessToken, sitePassword } from "@/lib/auth";

export async function proxy(request: NextRequest) {
  const password = sitePassword();
  if (!password) return NextResponse.next();

  const { pathname } = request.nextUrl;
  const token = request.cookies.get(accessCookieName())?.value;
  const expected = await accessToken(password);
  const authed = token === expected;

  if (pathname === "/login") {
    if (authed) return NextResponse.redirect(new URL("/", request.url));
    return NextResponse.next();
  }

  if (!authed) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|api/login|api/health|.*\\.(?:svg|png|jpg|ico)$).*)",
  ],
};

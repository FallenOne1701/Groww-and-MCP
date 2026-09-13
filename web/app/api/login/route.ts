import { NextRequest, NextResponse } from "next/server";
import { accessCookieName, accessToken, sitePassword } from "@/lib/auth";

export async function POST(request: NextRequest) {
  const expected = sitePassword();
  if (!expected) {
    return NextResponse.redirect(new URL("/", request.url));
  }

  const form = await request.formData();
  const password = String(form.get("password") ?? "");
  if (password !== expected) {
    return NextResponse.redirect(new URL("/login?error=1", request.url));
  }

  const response = NextResponse.redirect(new URL("/", request.url));
  response.cookies.set(accessCookieName(), await accessToken(expected), {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 60 * 60 * 24 * 7,
  });
  return response;
}

import { NextRequest, NextResponse } from 'next/server'

// ADR-081: Redirect legacy query-param URLs to the new Project Workspace routes.
// /settings/?project=X  →  /project/X/company
// /setup/?project=X     →  /project/X/repos
// /setup (no param)     stays  (setup wizard for new projects)
export function proxy(request: NextRequest) {
  const { pathname, searchParams } = request.nextUrl

  const project = searchParams.get('project')

  if (pathname === '/settings' && project) {
    return NextResponse.redirect(
      new URL(`/project/${encodeURIComponent(project)}/company`, request.url)
    )
  }

  if (pathname === '/setup' && project) {
    return NextResponse.redirect(
      new URL(`/project/${encodeURIComponent(project)}/repos`, request.url)
    )
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/settings', '/setup'],
}

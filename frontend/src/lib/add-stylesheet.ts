/**
 * Load a stylesheet into the document head with proper deduplication.
 */
export function addStylesheet(href: string): HTMLLinkElement | null {
  // Avoid loading the same stylesheet twice
  if (document.querySelector(`link[href="${href}"]`)) {
    return null;
  }

  const link = document.createElement("link");
  link.rel = "stylesheet";
  link.type = "text/css";
  link.href = href;
  document.head.appendChild(link);
  return link;
}
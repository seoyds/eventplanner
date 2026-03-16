"use client";

import React from "react";

// ─── A2UI Types ─────────────────────────────────────────────────────────────

export interface A2UISurface {
  surfaceId: string;
  components: A2UIComponent[];
  dataModel: Record<string, unknown>;
}

export interface A2UIComponent {
  id: string;
  component: string;
  [key: string]: unknown;
}

// ─── Data Binding Helpers ───────────────────────────────────────────────────

function resolveValue(
  value: unknown,
  dataModel: Record<string, unknown>
): unknown {
  if (value === null || value === undefined) return value;
  if (typeof value === "object" && value !== null && "path" in value) {
    const path = (value as { path: string }).path;
    return getByPath(dataModel, path);
  }
  if (typeof value === "object" && value !== null && "literalString" in value) {
    return (value as { literalString: string }).literalString;
  }
  if (typeof value === "object" && value !== null && "literalNumber" in value) {
    return (value as { literalNumber: number }).literalNumber;
  }
  return value;
}

function getByPath(obj: Record<string, unknown>, path: string): unknown {
  const parts = path.replace(/^\//, "").split("/");
  let current: unknown = obj;
  for (const part of parts) {
    if (current === null || current === undefined) return undefined;
    if (typeof current === "object") {
      current = (current as Record<string, unknown>)[part];
    } else {
      return undefined;
    }
  }
  return current;
}

function resolveString(
  value: unknown,
  dataModel: Record<string, unknown>
): string {
  const resolved = resolveValue(value, dataModel);
  return resolved !== null && resolved !== undefined ? String(resolved) : "";
}

function resolveArray(
  value: unknown,
  dataModel: Record<string, unknown>
): unknown[] {
  const resolved = resolveValue(value, dataModel);
  return Array.isArray(resolved) ? resolved : [];
}

// ─── Component Registry ─────────────────────────────────────────────────────

interface RendererProps {
  component: A2UIComponent;
  dataModel: Record<string, unknown>;
  allComponents: A2UIComponent[];
  onAction?: (actionName: string, context: Record<string, unknown>) => void;
}

function findChildren(
  parentId: string,
  allComponents: A2UIComponent[]
): A2UIComponent[] {
  return allComponents.filter((c) => c.parent === parentId);
}

function renderChildren(
  parentId: string,
  allComponents: A2UIComponent[],
  dataModel: Record<string, unknown>,
  onAction?: (actionName: string, context: Record<string, unknown>) => void
) {
  const children = findChildren(parentId, allComponents);
  return children.map((child) => (
    <A2UIComponentRenderer
      key={child.id}
      component={child}
      dataModel={dataModel}
      allComponents={allComponents}
      onAction={onAction}
    />
  ));
}

// ─── Text ───────────────────────────────────────────────────────────────────

function TextComponent({ component, dataModel }: RendererProps) {
  const text = resolveString(component.text, dataModel);
  const style = (component.style as string) || "body";

  const styleMap: Record<string, string> = {
    h1: "text-2xl font-bold mb-3 text-gray-900",
    h2: "text-xl font-semibold mb-2 text-gray-900",
    h3: "text-lg font-semibold mb-2 text-gray-800",
    h4: "text-base font-semibold mb-1 text-gray-800",
    h5: "text-sm font-semibold mb-1 text-gray-700",
    body: "text-sm text-gray-700 leading-relaxed",
    caption: "text-xs text-gray-500",
    label: "text-xs font-medium uppercase tracking-wide text-gray-500",
    overline: "text-xs font-medium uppercase tracking-wider text-gray-400",
  };

  const TagMap: Record<string, keyof JSX.IntrinsicElements> = {
    h1: "h1", h2: "h2", h3: "h3", h4: "h4", h5: "h5",
    body: "p", caption: "span", label: "span", overline: "span",
  };

  const Tag = TagMap[style] || "p";
  const className = styleMap[style] || styleMap.body;

  return <Tag className={className}>{text}</Tag>;
}

// ─── Card ───────────────────────────────────────────────────────────────────

function CardComponent({ component, dataModel, allComponents, onAction }: RendererProps) {
  const title = component.title
    ? resolveString(component.title, dataModel)
    : undefined;
  const subtitle = component.subtitle
    ? resolveString(component.subtitle, dataModel)
    : undefined;

  return (
    <div className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
      {(title || subtitle) && (
        <div className="px-5 pt-4 pb-2">
          {title && <h3 className="text-base font-semibold text-gray-900">{title}</h3>}
          {subtitle && <p className="text-sm text-gray-500 mt-0.5">{subtitle}</p>}
        </div>
      )}
      <div className="px-5 pb-4 space-y-2">
        {renderChildren(component.id, allComponents, dataModel, onAction)}
      </div>
    </div>
  );
}

// ─── Row ────────────────────────────────────────────────────────────────────

function RowComponent({ component, dataModel, allComponents, onAction }: RendererProps) {
  const gap = (component.gap as string) || "md";
  const align = (component.align as string) || "start";
  const wrap = component.wrap !== false;

  const gapMap: Record<string, string> = {
    xs: "gap-1", sm: "gap-2", md: "gap-3", lg: "gap-4", xl: "gap-6",
  };
  const alignMap: Record<string, string> = {
    start: "items-start", center: "items-center", end: "items-end",
    stretch: "items-stretch",
  };

  return (
    <div
      className={`flex ${wrap ? "flex-wrap" : ""} ${gapMap[gap] || "gap-3"} ${alignMap[align] || "items-start"}`}
    >
      {renderChildren(component.id, allComponents, dataModel, onAction)}
    </div>
  );
}

// ─── Column ─────────────────────────────────────────────────────────────────

function ColumnComponent({ component, dataModel, allComponents, onAction }: RendererProps) {
  const gap = (component.gap as string) || "md";
  const gapMap: Record<string, string> = {
    xs: "gap-1", sm: "gap-2", md: "gap-3", lg: "gap-4", xl: "gap-6",
  };

  return (
    <div className={`flex flex-col ${gapMap[gap] || "gap-3"}`}>
      {renderChildren(component.id, allComponents, dataModel, onAction)}
    </div>
  );
}

// ─── Button ─────────────────────────────────────────────────────────────────

function ButtonComponent({ component, dataModel, onAction }: RendererProps) {
  const label = resolveString(component.child || component.label, dataModel);
  const variant = (component.variant as string) || "primary";
  const disabled = component.disabled === true;
  const action = component.action as { name: string } | undefined;

  const variants: Record<string, string> = {
    primary:
      "bg-blue-600 text-white hover:bg-blue-700 shadow-sm",
    secondary:
      "bg-gray-100 text-gray-700 hover:bg-gray-200 border border-gray-300",
    outlined:
      "bg-transparent text-blue-600 hover:bg-blue-50 border border-blue-300",
    text: "bg-transparent text-blue-600 hover:bg-blue-50",
  };

  return (
    <button
      className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${variants[variant] || variants.primary} ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}
      disabled={disabled}
      onClick={() => {
        if (action?.name && onAction) {
          onAction(action.name, dataModel);
        }
      }}
    >
      {label}
    </button>
  );
}

// ─── Divider ────────────────────────────────────────────────────────────────

function DividerComponent() {
  return <hr className="border-gray-200 my-2" />;
}

// ─── Image ──────────────────────────────────────────────────────────────────

function ImageComponent({ component, dataModel }: RendererProps) {
  const src = resolveString(component.src, dataModel);
  const alt = component.alt ? resolveString(component.alt, dataModel) : "";
  const fit = (component.fit as string) || "cover";

  const fitMap: Record<string, string> = {
    cover: "object-cover",
    contain: "object-contain",
    fill: "object-fill",
  };

  return (
    <img
      src={src}
      alt={alt}
      className={`rounded-lg w-full max-h-48 ${fitMap[fit] || "object-cover"}`}
    />
  );
}

// ─── List ───────────────────────────────────────────────────────────────────

function ListComponent({ component, dataModel, allComponents, onAction }: RendererProps) {
  const items = component.items
    ? resolveArray(component.items, dataModel)
    : [];
  const templateChildren = findChildren(component.id, allComponents);
  const ordered = component.ordered === true;

  // If there are template children, render them for each item
  if (templateChildren.length > 0 && items.length > 0) {
    const Tag = ordered ? "ol" : "ul";
    return (
      <Tag className={`space-y-2 ${ordered ? "list-decimal" : "list-disc"} pl-5`}>
        {items.map((item, index) => {
          const itemModel = { ...dataModel, _item: item, _index: index };
          return (
            <li key={index} className="text-sm text-gray-700">
              {templateChildren.map((child) => (
                <A2UIComponentRenderer
                  key={`${child.id}-${index}`}
                  component={child}
                  dataModel={itemModel}
                  allComponents={allComponents}
                  onAction={onAction}
                />
              ))}
            </li>
          );
        })}
      </Tag>
    );
  }

  // Simple string list fallback
  if (items.length > 0) {
    const Tag = ordered ? "ol" : "ul";
    return (
      <Tag className={`space-y-1 ${ordered ? "list-decimal" : "list-disc"} pl-5`}>
        {items.map((item, index) => (
          <li key={index} className="text-sm text-gray-700">
            {String(item)}
          </li>
        ))}
      </Tag>
    );
  }

  // Children-only list
  return (
    <div className="space-y-2">
      {renderChildren(component.id, allComponents, dataModel, onAction)}
    </div>
  );
}

// ─── DataTable ──────────────────────────────────────────────────────────────

function DataTableComponent({ component, dataModel }: RendererProps) {
  const columns = (component.columns as Array<{ key: string; label: string; align?: string }>) || [];
  const rows = resolveArray(component.rows || component.data, dataModel) as Record<string, unknown>[];

  if (columns.length === 0 || rows.length === 0) {
    return <p className="text-sm text-gray-400 italic">No data</p>;
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            {columns.map((col) => (
              <th
                key={col.key}
                className={`px-4 py-2.5 text-xs font-semibold uppercase tracking-wider text-gray-500 ${col.align === "right" ? "text-right" : "text-left"}`}
              >
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 bg-white">
          {rows.map((row, i) => (
            <tr key={i} className="hover:bg-gray-50 transition-colors">
              {columns.map((col) => (
                <td
                  key={col.key}
                  className={`px-4 py-2.5 text-sm text-gray-700 ${col.align === "right" ? "text-right font-mono" : ""}`}
                >
                  {String(row[col.key] ?? "")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ─── Badge / Chip ───────────────────────────────────────────────────────────

function BadgeComponent({ component, dataModel }: RendererProps) {
  const text = resolveString(component.text || component.label, dataModel);
  const color = (component.color as string) || "gray";

  const colorMap: Record<string, string> = {
    gray: "bg-gray-100 text-gray-700",
    blue: "bg-blue-100 text-blue-700",
    green: "bg-green-100 text-green-700",
    yellow: "bg-yellow-100 text-yellow-700",
    red: "bg-red-100 text-red-700",
    purple: "bg-purple-100 text-purple-700",
  };

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${colorMap[color] || colorMap.gray}`}
    >
      {text}
    </span>
  );
}

// ─── ProgressBar ────────────────────────────────────────────────────────────

function ProgressBarComponent({ component, dataModel }: RendererProps) {
  const value = Number(resolveValue(component.value, dataModel) ?? 0);
  const max = Number(resolveValue(component.max, dataModel) ?? 100);
  const label = component.label
    ? resolveString(component.label, dataModel)
    : undefined;
  const pct = Math.min(100, Math.max(0, (value / max) * 100));

  const color =
    pct > 90 ? "bg-red-500" : pct > 70 ? "bg-yellow-500" : "bg-blue-500";

  return (
    <div className="w-full">
      {label && (
        <div className="flex justify-between text-xs text-gray-500 mb-1">
          <span>{label}</span>
          <span>{Math.round(pct)}%</span>
        </div>
      )}
      <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
        <div
          className={`h-full ${color} rounded-full transition-all duration-300`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

// ─── KeyValue ───────────────────────────────────────────────────────────────

function KeyValueComponent({ component, dataModel }: RendererProps) {
  const label = resolveString(component.label || component.key, dataModel);
  const value = resolveString(component.value, dataModel);

  return (
    <div className="flex justify-between items-baseline py-1">
      <span className="text-sm text-gray-500">{label}</span>
      <span className="text-sm font-medium text-gray-900">{value}</span>
    </div>
  );
}

// ─── Component Router ───────────────────────────────────────────────────────

const COMPONENT_MAP: Record<string, React.FC<RendererProps>> = {
  Text: TextComponent,
  Card: CardComponent,
  Row: RowComponent,
  Column: ColumnComponent,
  Button: ButtonComponent,
  Divider: DividerComponent,
  Image: ImageComponent,
  List: ListComponent,
  DataTable: DataTableComponent,
  Badge: BadgeComponent,
  ProgressBar: ProgressBarComponent,
  KeyValue: KeyValueComponent,
};

function A2UIComponentRenderer({
  component,
  dataModel,
  allComponents,
  onAction,
}: RendererProps) {
  const Renderer = COMPONENT_MAP[component.component];
  if (!Renderer) {
    // Unknown component — render as debug info in dev
    return (
      <div className="text-xs text-gray-400 italic">
        [Unknown: {component.component}]
      </div>
    );
  }
  return (
    <Renderer
      component={component}
      dataModel={dataModel}
      allComponents={allComponents}
      onAction={onAction}
    />
  );
}

// ─── Surface Renderer (Public API) ──────────────────────────────────────────

interface A2UISurfaceRendererProps {
  surface: A2UISurface;
  onAction?: (actionName: string, context: Record<string, unknown>) => void;
}

export function A2UISurfaceRenderer({
  surface,
  onAction,
}: A2UISurfaceRendererProps) {
  // Render only root components (those without a parent)
  const roots = surface.components.filter(
    (c) => !c.parent || c.parent === surface.surfaceId
  );

  return (
    <div className="space-y-3">
      {roots.map((comp) => (
        <A2UIComponentRenderer
          key={comp.id}
          component={comp}
          dataModel={surface.dataModel}
          allComponents={surface.components}
          onAction={onAction}
        />
      ))}
    </div>
  );
}

// ─── JSONL Message Parser ───────────────────────────────────────────────────

export function parseA2UIMessages(
  messages: A2UIMessage[],
  existing?: A2UISurface
): A2UISurface {
  const surface: A2UISurface = existing
    ? { ...existing, components: [...existing.components], dataModel: { ...existing.dataModel } }
    : { surfaceId: "default", components: [], dataModel: {} };

  for (const msg of messages) {
    if ("createSurface" in msg && msg.createSurface) {
      surface.surfaceId = msg.createSurface.surfaceId || "default";
    }
    if ("updateComponents" in msg && msg.updateComponents) {
      const incoming = msg.updateComponents.components || [];
      for (const comp of incoming) {
        const idx = surface.components.findIndex((c) => c.id === comp.id);
        if (idx >= 0) {
          surface.components[idx] = comp;
        } else {
          surface.components.push(comp);
        }
      }
    }
    if ("updateDataModel" in msg && msg.updateDataModel) {
      deepMerge(surface.dataModel, msg.updateDataModel.contents || {});
    }
    if ("deleteSurface" in msg && msg.deleteSurface) {
      surface.components = [];
      surface.dataModel = {};
    }
  }

  return surface;
}

export interface A2UIMessage {
  createSurface?: { surfaceId: string; theme?: string };
  updateComponents?: {
    surfaceId?: string;
    components: A2UIComponent[];
  };
  updateDataModel?: {
    surfaceId?: string;
    contents: Record<string, unknown>;
  };
  deleteSurface?: { surfaceId: string };
}

function deepMerge(
  target: Record<string, unknown>,
  source: Record<string, unknown>
): void {
  for (const key of Object.keys(source)) {
    if (
      source[key] &&
      typeof source[key] === "object" &&
      !Array.isArray(source[key]) &&
      target[key] &&
      typeof target[key] === "object" &&
      !Array.isArray(target[key])
    ) {
      deepMerge(
        target[key] as Record<string, unknown>,
        source[key] as Record<string, unknown>
      );
    } else {
      target[key] = source[key];
    }
  }
}

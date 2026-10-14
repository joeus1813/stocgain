"use client";
import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ColumnDef,
} from "@tanstack/react-table";
export function DataTable<T>({
  data,
  columns,
  sort,
  onSort,
  onRow,
}: {
  data: T[];
  columns: ColumnDef<T>[];
  sort?: { id: string; desc: boolean };
  onSort?: (id: string) => void;
  onRow?: (row: T) => void;
}) {
  "use no memo";
  // Manual sorting and pagination: PostgreSQL owns ordering across the full result.
  // TanStack v8 intentionally uses mutable table instances; this component opts out of compilation above.
  // eslint-disable-next-line react-hooks/incompatible-library
  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    manualSorting: true,
    manualPagination: true,
    state: { sorting: sort ? [sort] : [] },
  });
  return (
    <div className="table-scroll" tabIndex={0}>
      <table className="data-table sticky-table">
        <thead>
          {table.getHeaderGroups().map((group) => (
            <tr key={group.id}>
              {group.headers.map((h) => (
                <th
                  key={h.id}
                  aria-sort={
                    sort?.id === h.column.id
                      ? sort.desc
                        ? "descending"
                        : "ascending"
                      : undefined
                  }
                >
                  {onSort && h.column.getCanSort() ? (
                    <button onClick={() => onSort(h.column.id)}>
                      {flexRender(h.column.columnDef.header, h.getContext())}{" "}
                      {sort?.id === h.column.id ? (sort.desc ? "↓" : "↑") : "↕"}
                    </button>
                  ) : (
                    flexRender(h.column.columnDef.header, h.getContext())
                  )}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.map((row) => (
            <tr
              key={row.id}
              data-clickable={!!onRow}
              tabIndex={onRow ? 0 : undefined}
              onClick={onRow ? () => onRow(row.original) : undefined}
              onKeyDown={
                onRow
                  ? (e) => {
                      if (e.key === "Enter") onRow(row.original);
                    }
                  : undefined
              }
            >
              {row.getVisibleCells().map((cell) => (
                <td key={cell.id}>
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

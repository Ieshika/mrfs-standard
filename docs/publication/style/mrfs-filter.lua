-- Maps fenced divs to the MRFS callout and layout environments.
local boxes = {requirement = "mrfsrequirement", recommendation = "mrfsrecommendation",
               example = "mrfsexample", limitation = "mrfslimitation", note = "mrfsnote",
               formula = "mrfsformula", landscape = "widepage", references = "mrfsrefs",
               compact = "mrfscompact"}
function Div(el)
  for cls, env in pairs(boxes) do
    if el.classes:includes(cls) then
      local blocks = {pandoc.RawBlock("latex", "\\begin{" .. env .. "}")}
      for _, b in ipairs(el.content) do table.insert(blocks, b) end
      table.insert(blocks, pandoc.RawBlock("latex", "\\end{" .. env .. "}"))
      return blocks
    end
  end
  if el.classes:includes("pagebreak") then return pandoc.RawBlock("latex", "\\clearpage") end
end

-- Column widths from content: every column is at least as wide as its longest
-- unbreakable token (identifiers in code are weighted for the wider mono font),
-- and long text columns get proportionally more room.
local function cell_metrics(cell)
  local maxtok, len = 0, 0
  pandoc.walk_block(pandoc.Div(cell.contents), {
    Code = function(c) local w = #c.text * 1.15; maxtok = math.max(maxtok, w); len = len + w end,
    Str = function(s) local w = utf8.len(s.text) or #s.text; maxtok = math.max(maxtok, w); len = len + w + 1 end,
  })
  return maxtok, len
end

local numeric
function Table(tbl)
  local n = #tbl.colspecs
  local tok, long = {}, {}
  for i = 1, n do tok[i], long[i] = 0, 0 end
  local function scan(rows)
    for _, row in ipairs(rows) do
      for i, cell in ipairs(row.cells) do
        if i <= n then
          local t, l = cell_metrics(cell)
          tok[i] = math.max(tok[i], t); long[i] = math.max(long[i], l)
        end
      end
    end
  end
  scan(tbl.head.rows)
  for _, body in ipairs(tbl.bodies) do scan(body.body) end
  numeric = {}
  for i = 1, n do numeric[i] = {num = 0, total = 0} end
  for _, body in ipairs(tbl.bodies) do
    for _, row in ipairs(body.body) do
      for i, cell in ipairs(row.cells) do
        local t = pandoc.utils.stringify(pandoc.Div(cell.contents))
        if i <= n and t ~= "" and t ~= "RULE" then
          numeric[i].total = numeric[i].total + 1
          if t:match("^[%+%-−]?[%d%.,]+%%?$") then numeric[i].num = numeric[i].num + 1 end
        end
      end
    end
  end
  local need, total = {}, 0
  for i = 1, n do
    if long[i] <= 28 then
      need[i] = math.max(long[i] + 2, 5)            -- short phrases stay on one line
    else
      need[i] = math.max(tok[i] + 2.5, math.min(long[i], 48) * 0.6, 14)
    end
    total = total + need[i]
  end
  for i = 1, n do
    local align = tbl.colspecs[i][1]
    if numeric[i] and numeric[i].total > 0 and numeric[i].num == numeric[i].total then align = pandoc.AlignRight end
    tbl.colspecs[i] = {align, need[i] / total}
  end
  -- tables with seven or more columns are set one size smaller with tighter gaps,
  -- so that they stay portrait without wrapping intervals and status names
  if #tbl.colspecs >= 7 then
    return {pandoc.RawBlock("latex", "\\begin{mrfscompact}"), tbl, pandoc.RawBlock("latex", "\\end{mrfscompact}")}
  end
  return tbl
end

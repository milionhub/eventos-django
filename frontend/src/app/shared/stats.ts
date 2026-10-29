/** Whole-number percentage of `part` over `whole`; 0 when there is nothing to divide. */
export function percent(part: number, whole: number): number {
  return whole > 0 ? Math.round((part / whole) * 100) : 0;
}

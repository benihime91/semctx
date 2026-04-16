// Widget helpers.
// FEATURE: Demo Fixture.
export interface Widget {
  id: string;
}

export function buildWidget(id: string): Widget {
  return { id };
}

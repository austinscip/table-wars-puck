import { computeRecoverPlan } from '../ErrorBoundary';

describe('computeRecoverPlan (TV crash loop guard)', () => {
  it('recovers with exponential backoff under the cap', () => {
    expect(computeRecoverPlan(0, 6000, 5)).toMatchObject({ recover: true, delayMs: 6000 });
    expect(computeRecoverPlan(1, 6000, 5)).toMatchObject({ recover: true, delayMs: 12000 });
    expect(computeRecoverPlan(2, 6000, 5)).toMatchObject({ recover: true, delayMs: 24000 });
    // caps at 60s
    expect(computeRecoverPlan(4, 6000, 5)).toMatchObject({ recover: true, delayMs: 60000 });
  });

  it('gives up once the cap is exceeded (no endless flap)', () => {
    const plan = computeRecoverPlan(5, 6000, 5);
    expect(plan.recover).toBe(false);
    expect(plan.delayMs).toBe(0);
    expect(plan.nextAttempts).toBe(6);
  });
});

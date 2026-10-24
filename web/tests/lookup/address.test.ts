import { describe, expect, it, vi } from 'vitest';

import {
  AddressLookupController,
  lookupExportMetadata,
} from '../../src/lookup/controller';
import { MockGeocoder } from '../../src/lookup/mock';
import {
  createNoneGeocoder,
  LOOKUP_UNAVAILABLE_MESSAGE,
} from '../../src/lookup/none';
import { createLookupControl } from '../../src/lookup/ui';

const result = {
  id: 'result-1',
  label: 'Nearby public road',
  lon: -71.304,
  lat: 42.63,
};

describe('address lookup', () => {
  it('explains unavailable lookup and keeps curated views active', () => {
    const onCuratedViewpoints = vi.fn();
    const control = createLookupControl({
      provider: createNoneGeocoder(),
      onPlace: vi.fn(),
      onCuratedViewpoints,
    });
    document.body.append(control);

    expect(control.textContent).toContain(LOOKUP_UNAVAILABLE_MESSAGE);
    const input = control.querySelector('input');
    expect(input?.disabled).toBe(true);
    const curated = Array.from(control.querySelectorAll('button')).find(
      (button) => button.textContent === 'Use curated viewpoints',
    );
    curated?.click();
    expect(onCuratedViewpoints).toHaveBeenCalledOnce();
  });

  it('places a viewpoint from a mock result', async () => {
    const provider = new MockGeocoder([result]);
    const onPlace = vi.fn();
    const control = createLookupControl({
      provider,
      onPlace,
      onCuratedViewpoints: vi.fn(),
    });
    document.body.append(control);
    const input = control.querySelector('input');
    const form = control.querySelector('form');
    if (!input || !form) throw new Error('Lookup control is incomplete.');

    input.value = '10 Private Test Street';
    form.dispatchEvent(
      new Event('submit', { bubbles: true, cancelable: true }),
    );
    await vi.waitFor(() => expect(onPlace).toHaveBeenCalledWith(result));

    expect(input.value).toBe('');
    expect(provider.lastQuery).toBe('10 Private Test Street');
  });

  it('never puts the query in state, URL, or export data', async () => {
    const privateQuery = '42 Secret Test Avenue';
    const controller = new AddressLookupController(new MockGeocoder([result]));
    window.location.hash = '#mode=proposed';

    const results = await controller.search(privateQuery);
    const first = results[0];
    if (!first) throw new Error('Mock lookup returned no result.');
    controller.select(first);

    expect(JSON.stringify(controller.getState())).not.toContain(privateQuery);
    expect(window.location.hash).toBe('#mode=proposed');
    expect(JSON.stringify(lookupExportMetadata(controller))).not.toContain(
      privateQuery,
    );
  });
});

import { AddressLookupController } from './controller';
import type { Geocoder, GeocodeResult } from './types';

export interface LookupControlOptions {
  provider: Geocoder;
  onPlace: (result: GeocodeResult) => void;
  onCuratedViewpoints: () => void;
}

export function createLookupControl(
  options: LookupControlOptions,
): HTMLElement {
  const controller = new AddressLookupController(options.provider);
  const section = document.createElement('section');
  section.setAttribute('aria-labelledby', 'address-lookup-title');

  const heading = document.createElement('h2');
  heading.id = 'address-lookup-title';
  heading.textContent = 'Nearby address';

  const form = document.createElement('form');
  const label = document.createElement('label');
  label.htmlFor = 'address-lookup-input';
  label.textContent = 'Address';
  const input = document.createElement('input');
  input.id = 'address-lookup-input';
  input.name = 'address';
  input.type = 'search';
  input.autocomplete = 'street-address';
  input.disabled = !options.provider.available;
  const submit = document.createElement('button');
  submit.type = 'submit';
  submit.textContent = 'Find viewpoint';
  submit.disabled = !options.provider.available;
  const status = document.createElement('p');
  status.setAttribute('role', 'status');
  status.setAttribute('aria-live', 'polite');
  status.textContent = controller.getState().message;

  const curated = document.createElement('button');
  curated.type = 'button';
  curated.textContent = 'Use curated viewpoints';
  curated.addEventListener('click', options.onCuratedViewpoints);

  form.addEventListener('submit', (event) => {
    event.preventDefault();
    const activeQuery = input.value;
    input.value = '';
    status.textContent = 'Searching…';
    void controller.search(activeQuery).then((results) => {
      const first = results[0];
      if (first) {
        controller.select(first);
        options.onPlace(first);
      }
      status.textContent = controller.getState().message;
    });
  });

  form.append(label, input, submit);
  section.append(heading, form, status, curated);
  return section;
}

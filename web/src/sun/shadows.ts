import { Vector3, type DirectionalLight } from 'three';

import type { ConfidenceStatus } from '../data/types';
import type { SunPosition } from './position';

export const NEARBY_CONTEXT_SHADOW_RADIUS_M = 400;

export interface ShadowDecision {
  enabled: boolean;
  label: string;
  explanation: string;
}

export function shadowDecision(
  heightStatus: ConfidenceStatus,
  distanceFromSiteM: number,
  siteFeature: boolean,
): ShadowDecision {
  if (heightStatus === 'unknown') {
    return {
      enabled: false,
      label: 'No shadow',
      explanation: 'Height is unknown, so no shadow is shown.',
    };
  }
  if (!siteFeature && distanceFromSiteM > NEARBY_CONTEXT_SHADOW_RADIUS_M) {
    return {
      enabled: false,
      label: 'Shadow disabled',
      explanation: 'Only nearby context casts shadows.',
    };
  }
  if (heightStatus === 'estimated') {
    return {
      enabled: true,
      label: 'Estimated shadow',
      explanation: 'This shadow uses an estimated height.',
    };
  }
  return {
    enabled: true,
    label: 'Modeled shadow',
    explanation: 'This shadow uses a sourced height.',
  };
}

export function applySunPosition(
  light: DirectionalLight,
  position: SunPosition,
  target = new Vector3(),
  distanceM = 300,
): ShadowDecision {
  light.target.position.copy(target);
  if (position.altitudeDeg <= 0) {
    light.visible = false;
    return {
      enabled: false,
      label: 'Shadows disabled',
      explanation: 'The sun is below the horizon at this time.',
    };
  }

  const altitude = (position.altitudeDeg * Math.PI) / 180;
  const azimuth = (position.azimuthDeg * Math.PI) / 180;
  const horizontal = Math.cos(altitude);
  const direction = new Vector3(
    Math.sin(azimuth) * horizontal,
    Math.sin(altitude),
    -Math.cos(azimuth) * horizontal,
  );
  light.position.copy(target).addScaledVector(direction, distanceM);
  light.visible = true;
  light.castShadow = true;
  light.shadow.camera.left = -NEARBY_CONTEXT_SHADOW_RADIUS_M / 2;
  light.shadow.camera.right = NEARBY_CONTEXT_SHADOW_RADIUS_M / 2;
  light.shadow.camera.top = NEARBY_CONTEXT_SHADOW_RADIUS_M / 2;
  light.shadow.camera.bottom = -NEARBY_CONTEXT_SHADOW_RADIUS_M / 2;
  light.shadow.camera.updateProjectionMatrix();
  return {
    enabled: true,
    label: 'Shadows enabled',
    explanation: 'Shadows show the selected Lowell date and time.',
  };
}

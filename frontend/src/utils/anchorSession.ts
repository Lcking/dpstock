/**
 * Keep local email-binding state aligned with the server session.
 *
 * masked_email alone is not proof of an active bound session — JWT is required.
 */
import { apiService } from '@/services/api';
import {
  clearAnchorToken,
  clearMaskedEmail,
  getAnchorToken,
  getMaskedEmail,
  saveMaskedEmail,
} from '@/utils/anchorToken';

export type AnchorSessionMode = 'anchor' | 'anonymous' | 'restore';

export async function syncAnchorSession(): Promise<AnchorSessionMode> {
  const token = getAnchorToken();
  const localMasked = getMaskedEmail();

  if (!token && localMasked) {
    clearAnchorToken();
    clearMaskedEmail();
    return 'restore';
  }

  try {
    const data = await apiService.getAnchorStatus();
    if (data?.mode === 'anchor') {
      if (data.masked_email) {
        saveMaskedEmail(data.masked_email);
      }
      return token ? 'anchor' : 'restore';
    }

    if (token || localMasked) {
      localStorage.removeItem('token');
      clearAnchorToken();
      clearMaskedEmail();
      return 'restore';
    }

    return 'anonymous';
  } catch {
    if (!token && localMasked) {
      clearAnchorToken();
      clearMaskedEmail();
      return 'restore';
    }
    return token && localMasked ? 'anchor' : 'anonymous';
  }
}

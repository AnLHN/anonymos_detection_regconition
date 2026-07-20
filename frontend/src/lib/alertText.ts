import type { Alert } from './types';

const WARNING_TEXT: Record<string, string> = {
  stable_unknown_face: 'Phát hiện người lạ',
  unknown_outside_working_hours: 'Người lạ ngoài giờ',
  unknown_loitering_at_gate: 'Đứng lâu ở cổng',
  unknown_entered_restricted_area: 'Vào vùng hạn chế',
  unverified_in_restricted_area: 'Chưa xác minh vào vùng hạn chế',
};

const LEVEL_TEXT: Record<string, string> = {
  low: 'Thấp',
  medium: 'Trung bình',
  high: 'Cao',
  critical: 'Khẩn cấp',
};

const REVIEW_TEXT: Record<string, string> = {
  new: 'Mới',
  reviewing: 'Đang kiểm tra',
  confirmed: 'Đã xác nhận',
  false_positive: 'Báo sai',
  ignored: 'Bỏ qua',
};

const ZONE_TRANSLATIONS: Record<string, string> = {
  restricted_area: 'Khu vực hạn chế',
  server_room: 'Phòng máy chủ',
  warehouse: 'Kho hàng',
  gate: 'Cổng',
  lobby_gate: 'Cổng sảnh',
  lobby: 'Sảnh',
};

export function translateZone(zone: string): string {
  if (!zone || zone === 'none') return '';
  const trimmed = zone.trim();
  return ZONE_TRANSLATIONS[trimmed] || humanizeCode(trimmed);
}

export function alertTitle(alert: Alert) {
  return WARNING_TEXT[alert.warning_type] || humanizeCode(alert.warning_type || alert.status || 'Cảnh báo an ninh');
}

export function warningTypeText(type: string) {
  return WARNING_TEXT[type] || humanizeCode(type || 'Cảnh báo khác');
}

export function alertSummary(alert: Alert) {
  const zone = alert.zone && alert.zone !== 'none' ? ` tại ${translateZone(alert.zone)}` : '';
  return `${alert.camera_id}${zone}`;
}

export function alertLevelText(level: string) {
  return LEVEL_TEXT[level] || humanizeCode(level);
}

export function reviewText(status: string) {
  return REVIEW_TEXT[status] || humanizeCode(status);
}

export function alertDetailReason(alert: Alert) {
  return translateReason(alert.reason) || alertTitle(alert);
}

export function translateReason(reason?: string | null): string {
  if (!reason) return '';
  
  // Track 355 stayed unknown for at least 1.5s
  let match = reason.match(/Track (\d+) stayed unknown for at least ([\d.]+)s/i);
  if (match) {
    return `Đối tượng (Track ${match[1]}) duy trì trạng thái người lạ quá ${match[2]} giây.`;
  }
  
  // Unknown track 355 entered restricted zone warehouse
  match = reason.match(/Unknown track (\d+) entered restricted zone (\w+)/i);
  if (match) {
    return `Người lạ (Track ${match[1]}) đã đi vào khu vực hạn chế: ${translateZone(match[2])}.`;
  }
  
  // Unknown track 355 appeared outside working hours
  match = reason.match(/Unknown track (\d+) appeared outside working hours/i);
  if (match) {
    return `Người lạ (Track ${match[1]}) xuất hiện ngoài giờ làm việc.`;
  }
  
  // Unknown track 355 stayed in gate zone for 12 processed frames
  match = reason.match(/Unknown track (\d+) stayed in gate zone for (\d+) processed frames/i);
  if (match) {
    return `Người lạ (Track ${match[1]}) đứng lâu tại khu vực cổng (${match[2]} khung hình).`;
  }
  
  // Unverified track 355 appeared in restricted zone server_room
  match = reason.match(/Unverified track (\d+) appeared in restricted zone (\w+)/i);
  if (match) {
    return `Đối tượng chưa xác minh (Track ${match[1]}) đi vào khu vực hạn chế: ${translateZone(match[2])}.`;
  }
  
  return reason;
}

function humanizeCode(value: string) {
  return value
    .replaceAll('_', ' ')
    .split(' ')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}


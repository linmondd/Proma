/**
 * 定时任务完成通知投递服务。
 *
 * 外部 IM 通知通道已退役；保留入口，避免调度器调用方需要关心通知实现细节。
 */

import type {
  Automation,
  AutomationRun,
} from '@proma/shared'

interface AutomationNotificationPayload {
  automation: Automation
  run: AutomationRun
}

export async function notifyAutomationRunFinished(payload: AutomationNotificationPayload): Promise<void> {
  void payload
}

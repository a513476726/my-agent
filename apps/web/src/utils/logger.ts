/**
 * 日志工具
 */
import envConfig from '@/config/env'

export type LogLevel = 'debug' | 'info' | 'warn' | 'error'

class Logger {
  private logLevel: LogLevel
  private debugMode: boolean

  constructor() {
    this.logLevel = envConfig.LOG_LEVEL
    this.debugMode = envConfig.DEBUG
  }

  private shouldLog(level: LogLevel): boolean {
    const levels: Record<LogLevel, number> = {
      debug: 0,
      info: 1,
      warn: 2,
      error: 3,
    }
    return levels[level] >= levels[this.logLevel]
  }

  private formatMessage(level: LogLevel, message: string, ...args: any[]): void {
    if (!this.shouldLog(level)) return

    const timestamp = new Date().toISOString()
    const prefix = `[${timestamp}] [${level.toUpperCase()}]`

    switch (level) {
      case 'debug':
        if (this.debugMode) {
          console.debug(prefix, message, ...args)
        }
        break
      case 'info':
        console.info(prefix, message, ...args)
        break
      case 'warn':
        console.warn(prefix, message, ...args)
        break
      case 'error':
        console.error(prefix, message, ...args)
        break
    }
  }

  debug(message: string, ...args: any[]): void {
    this.formatMessage('debug', message, ...args)
  }

  info(message: string, ...args: any[]): void {
    this.formatMessage('info', message, ...args)
  }

  warn(message: string, ...args: any[]): void {
    this.formatMessage('warn', message, ...args)
  }

  error(message: string, ...args: any[]): void {
    this.formatMessage('error', message, ...args)
  }

  // API 请求日志
  apiRequest(method: string, url: string, data?: any): void {
    this.debug(`API Request: ${method.toUpperCase()} ${url}`, data)
  }

  apiResponse(method: string, url: string, status: number, data?: any): void {
    if (status >= 400) {
      this.error(`API Error: ${method.toUpperCase()} ${url} - ${status}`, data)
    } else {
      this.debug(`API Response: ${method.toUpperCase()} ${url} - ${status}`, data)
    }
  }

  // 用户行为日志
  userAction(action: string, details?: any): void {
    this.info(`User Action: ${action}`, details)
  }

  // 性能日志
  performance(name: string, duration: number): void {
    this.debug(`Performance: ${name} took ${duration}ms`)
  }
}

// 创建全局日志实例
export const logger = new Logger()

// 默认导出
export default logger

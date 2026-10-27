import dayjs from 'dayjs'
import 'dayjs/locale/zh-cn'
import utc from 'dayjs/plugin/utc'
import timezone from 'dayjs/plugin/timezone'
import relativeTime from 'dayjs/plugin/relativeTime'
import duration from 'dayjs/plugin/duration'
import customParseFormat from 'dayjs/plugin/customParseFormat'
dayjs.locale('zh-cn')

dayjs.extend(utc)
dayjs.extend(timezone)
dayjs.extend(relativeTime)
dayjs.extend(duration)
dayjs.extend(customParseFormat)

export default dayjs

import SearchInput from './SearchInput.vue'
import SearchSelect from './SearchSelect.vue'
import SearchDatePicker from './SearchDatePicker.vue'
import SearchDateRangePicker from './SearchDateRangePicker.vue'
import SearchInputNumber from './SearchInputNumber.vue'
import SearchAsyncSelect from './SearchAsyncSelect.vue'

export {
  SearchInput,
  SearchSelect,
  SearchDatePicker,
  SearchDateRangePicker,
  SearchInputNumber,
  SearchAsyncSelect,
}

export const fieldComponents: Record<string, any> = {
  input: SearchInput,
  select: SearchSelect,
  date: SearchDatePicker,
  dateRange: SearchDateRangePicker,
  inputNumber: SearchInputNumber,
  asyncSelect: SearchAsyncSelect,
}

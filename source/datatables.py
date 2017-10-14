# Datatable server side processing
# @author : Ahmad Fajar
# support : ordering single or multiple column, searching from specify column
# minus : searching from all column, regex

# how to use:
# first on the client side should be have this 2 params option in your datatables initial script:
# serverSide : true,
# columns: [
#   { 'name' : 'dbFieldName/specificKeyFromResponse', 'data' : 'dbFieldName/specificKeyFromResponse/YouCreateCallbackinHere' }
# ]

# then we create an object from Datatables Class
# in here we pass all the data from datatables in request.GET then assign that to `attributes` args
# and the Model Class into `queryset` args like this :
# DT_Instance = Datatables(attributes=request.GET, queryset=ModelClass)

# then we just call the filter function and get query result like this:
# datas, records_filtered, records_total = DI_Instance.filter().getQueryset()
# and then we return the response to client side or we can play with the datas first and then return the response to clien side
# return JsonResponse({
#     "draw": DT_Instance.getDraw(),
#     "data" : list(datas.values('columnA', 'columnB', 'etc..')),
#     "recordsTotal": records_total,
#     "recordsFiltered": records_filtered
# }, safe=False)


# important NOTE :
# the default filter condition is just like this `column=value`
# so if we have a special condition like `column__lte` or etc,
# we can create a function to filter with condition what we want like this:
# in this case we want to filter the date data by month and day
# def monthday_filter(value, column='')
#   mn, day = value.split('-')
#   NOTE : the return function should be Boolean False or array 2 dimension `[[condition, value], etc...]`
#   if we return False the custom function will not be executed
#   return [['%s__month'%(column), mn], ['%s__day'%(column), day]]

# then we assign the function into custom_condition args and we can also add an extra filter in filter function like this
# custom_condition = { 'nametheDateField' : monthday_filter }
# DT_Instance.filter(filters={'a' : 'a', 'b' :'b'}, custom_condition=custom_condition)
#
# then we get the query result with data that already filtered by condition what we want from datatables and what we do previously
# datas, records_filtered, records_total = DI_Instance.getQueryset()

class Datatables():
    # attributes format from datatables will be like this:
    # {
        # 'draw': [''],
        # 'columns[0-n][data]': ['0'],
        # 'columns[0-n][name]': [''],
        # 'columns[0-n][searchable]': ['true' or 'false'],
        # 'columns[0-n][orderable]': ['true' or 'false'],
        # 'columns[0-n][search][value]': [''],
        # 'columns[0-n][search][regex]': ['true' or 'false']
        # 'order[0][column]': ['2'],
        # 'order[0][dir]': ['desc'],
        # 'start': ['0'],
        # 'length': ['100'],
        # 'search[value]': [''],
        # 'search[regex]': ['false']
    # }
    # we get raw attributes from request.GET
    rawAttributes = {}

    # we want the attribute from datatables more readable
    cleanAttributes = {'columns' : [], 'order' : [], 'start' : 0, 'length' : 10, 'search' : {'value' : '', 'regex' : 'false'}}

    # direction ordering
    direction_order = {
        'desc' : '-',
        'asc' : ''
    }

    # data from database
    queryset = None

    def __init__(self, attributes={}, queryset=None):
        # we pass request.GET to rawAttributes
        self.rawAttributes = attributes
        # queryset is the model object
        self.queryset = queryset

        # we normalize the attributes first
        if queryset:
            self.normalizeAttributes()

    def normalizeAttributes(self):
        # reset order and columns
        self.cleanAttributes['order'] = []
        self.cleanAttributes['columns'] = []

        i = 0
        loop = True
        while loop:
            # first we normalize each column attributes
            try:
                name = self.rawAttributes['columns[%d][name]'%(i)]
                data = {
                    'data' : self.rawAttributes['columns[%d][data]'%(i)],
                    'name' : name,
                    'searchable' : self.rawAttributes['columns[%d][searchable]'%(i)],
                    'orderable' : self.rawAttributes['columns[%d][orderable]'%(i)],
                    'search' : {
                        'value' : self.rawAttributes['columns[%d][search][value]'%(i)],
                        'regex' : self.rawAttributes['columns[%d][search][regex]'%(i)]
                    }
                }
                self.cleanAttributes['columns'].append(data)
                i+=1
            except Exception as e:
                loop = False

        i = 0
        loop = True
        while loop:
            # normalize order
            try:
                self.cleanAttributes['order'].append({
                    'column' : self.rawAttributes['order[%d][column]'%(i)],
                    'dir' : self.rawAttributes['order[%d][dir]'%(i)]
                })
                i+=1
            except Exception as e:
                loop = False

        # normalize all global attributes
        self.cleanAttributes['start'] = int(self.rawAttributes['start'])
        self.cleanAttributes['draw'] = self.rawAttributes['draw']
        self.cleanAttributes['length'] = int(self.rawAttributes['length'])
        self.cleanAttributes['search']['value'] = self.rawAttributes['search[value]']
        self.cleanAttributes['search']['regex'] = self.rawAttributes['search[regex]']

    def globalFilter(self, filters, custom_orders, q_filters):
        order_by = []
        # order by
        for order in self.cleanAttributes['order']:
            column = self.cleanAttributes['columns'][int(order['column'])]['name']
            try:
                # we can create a custom function for ordering with any condition what we want
                columns = custom_orders[column]()
                if columns:
                    for ccolumn in columns:
                        ccolumn = self.direction_order[order['dir']] + ccolumn
                        order_by.append(ccolumn)
            except Exception as e:
                column = self.direction_order[order['dir']] + column
                if column not in order_by:
                    order_by.append(column)

        self.queryset = self.queryset.objects.order_by(*order_by).filter(**filters)

        if q_filters and self.cleanAttributes['search']['value'] != '':
            self.queryset = self.queryset.filter(q_filters(self.cleanAttributes['search']['value']))

        return self

    def filters(self, custom_condition={}, filters={}, custom_orders={}, globalSearch=False, q_filters=None):
        if globalSearch:
            return self.globalFilter(filters, custom_orders, q_filters)

        order_by = []
        # search
        for column in self.cleanAttributes['columns']:
            if column['search']['value'] != '':
                value = column['search']['value']

                # default condition just a name of field
                condition = column['name']
                try:
                    # we can create a custom function for filter with any condition what we want
                    conditions = custom_condition[condition](value=value, column=condition)
                    if conditions:
                        for cn, val in conditions:
                            filters[cn] = None if val == 'null' else val

                except Exception as e:
                    filters[condition] = None if value == 'null' else value

        # order by
        for order in self.cleanAttributes['order']:
            column = self.cleanAttributes['columns'][int(order['column'])]['name']
            try:
                # we can create a custom function for ordering with any condition what we want
                columns = custom_orders[column]()
                if columns:
                    for ccolumn in columns:
                        ccolumn = self.direction_order[order['dir']] + ccolumn
                        order_by.append(ccolumn)
            except Exception as e:
                column = self.direction_order[order['dir']] + column
                if column not in order_by:
                    order_by.append(column)

        self.queryset = self.queryset.objects.order_by(*order_by).filter(**filters)

        return self

    def exclude(self, **filters):
        self.queryset = self.queryset.exclude(**filters)
        return self

    # setter getter
    def getQueryset(self, full=False):
        querysetByRange = None
        try:
            querysetByRange = self.queryset[self.getStart():self.getEnd()]
        except Exception as e:
            pass
        if not full:
            return [querysetByRange, self.queryset.count(), len(querysetByRange)]
        else:
            return [self.queryset, self.queryset.count()]

    def getAttributes(self, attribute=None):
        if attribute:
            attribute = self.cleanAttributes[attribute]
        else:
            attribute = self.cleanAttributes

        return attribute

    def getLength(self):
        return self.cleanAttributes['length']

    def getDraw(self):
        return self.cleanAttributes['draw']

    def getStart(self):
        return self.cleanAttributes['start']

    def getEnd(self):
        return self.cleanAttributes['start'] + self.cleanAttributes['length']

    def getOrders(self):
        order_by = []
        self.normalizeAttributes()
        for order in self.cleanAttributes['order']:
            column = self.cleanAttributes['columns'][int(order['column'])]['name']
            column = self.direction_order[order['dir']] + column
            if column not in order_by:
                order_by.append(column)

        return order_by

    def getFilters(self):
        order_by = []
        self.normalizeAttributes()
        filters = {}
        # search
        for column in self.cleanAttributes['columns']:
            if column['search']['value'] != '':
                value = column['search']['value']

                # default condition just a name of field
                condition = column['name']
                try:
                    # we can create a custom function for filter with any condition what we want
                    conditions = custom_condition[condition](value=value, column=condition)
                    if conditions:
                        for cn, val in conditions:
                            filters[cn] = None if val == 'null' else val

                except Exception as e:
                    filters[condition] = None if value == 'null' else value

        return filters

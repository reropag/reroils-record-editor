angular.module('reroilseditor', ['schemaForm'])
    .controller('FormController', function($scope, $http, $window) {

        $scope.params = {
            form: ["*"],
            model: {},
            schema: {}
        };

        $scope.message = {
            title:"",
            content: "",
            type: ""
        };

        function editorInit(init, form, schema, model) {
            $scope.params.schema = angular.fromJson(schema);
            $scope.params.model = angular.fromJson(model);
            $scope.params.form = angular.fromJson(form);
        };

        $scope.$on('edit.init', editorInit);
        $scope.importEanFromBnf = function(test) {
          var isbn = $scope.params.model.identifiers.isbn;
          var schema = $scope.params.model['$schema'];
          $http({
              method: 'GET',
                  url: '/editor/import/bnf/ean/' + isbn
              }).then(function successCallback(response) {
                  $scope.params.model = response.data;
                  $scope.message.type = 'success';
                  $scope.message.content = 'import done.';
                  $scope.message.title = 'Success:';
                  $scope.params.model['$schema'] = schema;
              }, function errorCallback(response) {
                  if (response.status === 404) {
                      $scope.message.type = 'warning';
                      $scope.message.content = 'Record not found given isbn: ' + isbn + '.';
                      $scope.message.title = 'Warning:';
                      $scope.params.model = {'identifiers':{'isbn': isbn}};
                  } else {
                      $scope.message.type = 'danger';
                      $scope.message.content = 'An error occured on the remote server.';
                      $scope.message.title = 'Error:';
                      $scope.params.model = {'identifiers':{'isbn': isbn}};
                  }
                  $scope.params.model['$schema'] = schema;
          });
        }

        $scope.onSubmit = function(form) {
            // First we broadcast an event so all fields validate themselves
            $scope.$broadcast('schemaFormValidate');

            // Then we check if the form is valid
            if (form.$valid) {
                $http({
                        method: 'POST',
                        data: $scope.params.model,
                        url: '/editor/records/save'
                    }).then(function successCallback(response) {
                        $window.location.href = '/records/' + response.data.pid;
                    }, function errorCallback(response) {
                        $scope.message.type = 'danger';
                        $scope.message.content = 'An error occurs during the data submission.';
                        $scope.message.title = 'Error:';
                });
            }
        }
    })

    .directive('ngInitial', function($parse) {
        return {
            restrict: 'E',
            scope: false,
            controller: 'FormController',
            link: function (scope, element, attrs) {
                scope.$broadcast(
                    'edit.init', attrs.form, attrs.schema, attrs.model
                );
            }
        }
    })
    .directive('alert', function() {
        return {
            'template': '<div ng-show="message.title" class="alert alert-{{message.type}}"><strong>{{message.title}}</strong> {{message.content}}</div>'
        }
    });

(function (angular) {
    // Bootstrap it!
    angular.element(document).ready(function() {
        angular.bootstrap(
            document.getElementById("reroils-editor"), [
                'schemaForm',
                'reroilseditor'
            ]
        );
    });
})(angular);

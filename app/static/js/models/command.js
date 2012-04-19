// Command model

window.Todo = Backbone.Model.extend({

  // Default attributes for the todo.
  defaults: {
    cmd: '',
    description: '',
    example: '',
    isGlobal:false,
    switches : '',
    includes : '',
    excludes : '',
    dateUpdated: Date.now(),
  },

  // Ensure that each todo created has `content`.
  initialize: function() {
    if (!this.get("content")) {
      this.set({"content": this.defaults.content});
    }
  },

  // Toggle the `done` state of this todo item.
  toggle: function() {
    this.save({done: !this.get("done")});
  },

  // Remove this Todo from *localStorage* and delete its view.
  clear: function() {
    this.destroy();
    this.view.remove();
  }

});

// Command Collection
window.CommandsList = Backbone.Collection.extend({

  // Reference to this collection's model.
  model: Command,
  url :'/commands',

  // Filter down the list of all todo items that are finished.
  done: function() {
    return this.filter(function(todo){ return todo.get('done'); });
  },

  // Filter down the list to only todo items that are still not finished.
  remaining: function() {
    return this.without.apply(this, this.done());
  },

  // We keep the Todos in sequential order, despite being saved by unordered
  // GUID in the database. This generates the next order number for new items.
  nextOrder: function() {
    if (!this.length) return 1;
    return this.last().get('order') + 1;
  },

  // Todos are sorted by their original insertion order.
  comparator: function(todo) {
    return todo.get('order');
  }

});
